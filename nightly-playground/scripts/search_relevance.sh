#!/bin/sh

# This script sets up sample data to exercise the features of the Search Relevance Workbench.
#
# ./search-relevance.sh --url https://${{needs.validate-and-deploy.outputs.ENDPOINT}}/${{needs.validate-and-deploy.outputs.PLAYGROUND_ID}}
#
# It will clear out any existing indexes as part of running it.

# Helper script for capturing return values from curl commands
exe() { (set -x ; "$@") | jq | tee RES; echo; }


# Default URL if not provided
OPENSEARCH_SERVER_URL=${OPENSEARCH_SERVER_URL:-"$OPENSEARCH_SERVER_URL"}

# Allow command-line override
if [ "$1" = "--url" ] && [ -n "$2" ]; then
  OPENSEARCH_SERVER_URL="$2"
  shift 2
fi

echo "Using OpenSearch server: $OPENSEARCH_SERVER_URL"

echo Deleting ecommerce sample data
(curl -s -X DELETE "$OPENSEARCH_SERVER_URL/ecommerce" > /dev/null) || true

ECOMMERCE_DATA_FILE="esci_us_opensearch-2025-06-06.json"
# Check if data file exists locally, if not download it
if [ ! -f "$ECOMMERCE_DATA_FILE" ]; then
  echo "Data file not found locally. Downloading from S3..."
  wget https://o19s-public-datasets.s3.amazonaws.com/esci_us_opensearch-2025-06-06.json
fi

echo "Creating ecommerce index using default bulk ingestion schema"

# Create the index by reading in one doc
head -n 2 "$ECOMMERCE_DATA_FILE" | curl -s -X POST "$OPENSEARCH_SERVER_URL/index-name/_bulk?pretty" \
  -H 'Content-Type: application/x-ndjson' --data-binary @-

echo
echo Populating ecommerce index
  
# Get total line count of the file
TOTAL_LINES=$(wc -l < "$ECOMMERCE_DATA_FILE")
echo "Total lines in file: $TOTAL_LINES"

# Calculate number of chunks (50000 lines per chunk)
CHUNK_SIZE=50000
CHUNKS=$(( (TOTAL_LINES + CHUNK_SIZE - 1) / CHUNK_SIZE ))
echo "Will process file in $CHUNKS chunks of $CHUNK_SIZE lines each"

# Process file in chunks
for (( i=0; i<CHUNKS; i++ )); do
  START_LINE=$(( i * CHUNK_SIZE + 1 ))
  END_LINE=$(( (i + 1) * CHUNK_SIZE ))
  
  # Ensure we don't go past the end of the file
  if [ $END_LINE -gt $TOTAL_LINES ]; then
    END_LINE=$TOTAL_LINES
  fi
  
  LINES_TO_PROCESS=$(( END_LINE - START_LINE + 1 ))
  echo "Processing chunk $((i+1))/$CHUNKS: lines $START_LINE-$END_LINE ($LINES_TO_PROCESS lines)"
  
  # Use sed to extract the chunk and pipe to curl for indexing
  sed -n "${START_LINE},${END_LINE}p" "$ECOMMERCE_DATA_FILE" | \
    curl -s -o /dev/null -w "%{http_code}" -X POST "$OPENSEARCH_SERVER_URL/ecommerce/_bulk" \
    -H 'Content-Type: application/x-ndjson' --data-binary @- 
  
  # Give OpenSearch a moment to process the chunk
  sleep 1
done

echo "All data indexed successfully"


echo Deleting UBI indexes
(curl -s -X DELETE "$OPENSEARCH_SERVER_URL/ubi_queries" > /dev/null) || true
(curl -s -X DELETE "$OPENSEARCH_SERVER_URL/ubi_events" > /dev/null) || true

echo Creating UBI indexes using mappings
curl -s -X POST "$OPENSEARCH_SERVER_URL/_plugins/ubi/initialize"

echo Loading sample UBI data
curl -o /dev/null -X POST "$OPENSEARCH_SERVER_URL/index-name/_bulk?pretty" --data-binary @../sample-data/search-relevance/ubi_queries_events.ndjson -H "Content-Type: application/x-ndjson"

echo Refreshing UBI indexes to make indexed data available for query sampling
curl -XPOST "$OPENSEARCH_SERVER_URL/ubi_queries/_refresh"
echo
curl -XPOST "$OPENSEARCH_SERVER_URL/ubi_events/_refresh"

read -r -d '' QUERY_BODY << EOF
{
  "query": {
    "match_all": {}
  },
  "size": 0
}
EOF

NUMBER_OF_QUERIES=$(curl -s -XGET "$OPENSEARCH_SERVER_URL/ubi_queries/_search" \
  -H "Content-Type: application/json" \
  -d "${QUERY_BODY}" | jq -r '.hits.total.value')

NUMBER_OF_EVENTS=$(curl -s -XGET "$OPENSEARCH_SERVER_URL/ubi_events/_search" \
  -H "Content-Type: application/json" \
  -d "${QUERY_BODY}" | jq -r '.hits.total.value')
  
echo
echo "Indexed UBI data: $NUMBER_OF_QUERIES queries and $NUMBER_OF_EVENTS events"

echo Deleting queryset, search config, judgment and experiment indexes
(curl -s -X DELETE "$OPENSEARCH_SERVER_URL/search-relevance-search-config" > /dev/null) || true
(curl -s -X DELETE "$OPENSEARCH_SERVER_URL/search-relevance-queryset" > /dev/null) || true
(curl -s -X DELETE "$OPENSEARCH_SERVER_URL/search-relevance-judgment" > /dev/null) || true
(curl -s -X DELETE "$OPENSEARCH_SERVER_URL/.plugins-search-relevance-experiment" > /dev/null) || true
(curl -s -X DELETE "$OPENSEARCH_SERVER_URL/search-relevance-evaluation-result" > /dev/null) || true
(curl -s -X DELETE "$OPENSEARCH_SERVER_URL/search-relevance-experiment-variant" > /dev/null) || true

sleep 2
echo Create search configs

exe curl -s -X PUT "$OPENSEARCH_SERVER_URL/_plugins/_search_relevance/search_configurations" \
-H "Content-type: application/json" \
-d'{
      "name": "baseline",
      "query": "{\"query\":{\"multi_match\":{\"query\":\"%SearchText%\",\"fields\":[\"id\",\"title\",\"category\",\"bullet_points\",\"description\",\"brand\",\"color\"]}}}",
      "index": "ecommerce"
}'

SC_BASELINE=`jq -r '.search_configuration_id' < RES`

exe curl -s -X PUT "$OPENSEARCH_SERVER_URL/_plugins/_search_relevance/search_configurations" \
-H "Content-type: application/json" \
-d'{
      "name": "baseline with title weight",
      "query": "{\"query\":{\"multi_match\":{\"query\":\"%SearchText%\",\"fields\":[\"id\",\"title^25\",\"category\",\"bullet_points\",\"description\",\"brand\",\"color\"]}}}",
      "index": "ecommerce"
}'

SC_CHALLENGER=`jq -r '.search_configuration_id' < RES`

echo
echo List search configurations
exe curl -s -X GET "$OPENSEARCH_SERVER_URL/_plugins/_search_relevance/search_configurations" \
-H "Content-type: application/json" \
-d'{
     "sort": {
       "timestamp": {
         "order": "desc"
       }
     },
     "size": 10
   }'

echo
echo Baseline search config id: $SC_BASELINE
echo Challenger search config id: $SC_CHALLENGER

echo
echo Create Query Sets by Sampling UBI Data
exe curl -s -X POST "$OPENSEARCH_SERVER_URL/_plugins/_search_relevance/query_sets" \
-H "Content-type: application/json" \
-d'{
   	"name": "Top 20",
   	"description": "Top 20 most frequent queries sourced from user searches.",
   	"sampling": "topn",
   	"querySetSize": 20
}'

QUERY_SET_UBI=`jq -r '.query_set_id' < RES`

sleep 2

echo
echo Upload Manually Curated Query Set 

exe curl -s -X PUT "$OPENSEARCH_SERVER_URL/_plugins/_search_relevance/query_sets" \
-H "Content-type: application/json" \
-d'{
   	"name": "TVs",
   	"description": "Some TVs that people might want",
   	"sampling": "manual",
   	"querySetQueries": [
    	{"queryText": "tv"},
    	{"queryText": "led tv"}
    ]
}'

QUERY_SET_MANUAL=`jq -r '.query_set_id' < RES`

echo
echo Upload ESCI Query Set 

exe curl -s -X PUT "$OPENSEARCH_SERVER_URL/_plugins/_search_relevance/query_sets" \
-H "Content-type: application/json" \
--data-binary @../sample-data/search-relevance/esci_us_queryset.json



QUERY_SET_ESCI=`jq -r '.query_set_id' < RES`

echo
echo List Query Sets

exe curl -s -X GET "$OPENSEARCH_SERVER_URL/_plugins/_search_relevance/query_sets" \
-H "Content-type: application/json" \
-d'{
     "sort": {
       "sampling": {
         "order": "desc"
       }
     },
     "size": 10
   }'

echo
echo Create Implicit Judgments
exe curl -s -X PUT "$OPENSEARCH_SERVER_URL/_plugins/_search_relevance/judgments" \
-H "Content-type: application/json" \
-d'{
   	"clickModel": "coec",
    "maxRank": 20,
   	"name": "Implicit Judgements",
   	"type": "UBI_JUDGMENT"
  }'
  
UBI_JUDGMENT_LIST_ID=`jq -r '.judgment_id' < RES`

# wait for judgments to be created in the background
sleep 2

echo
echo Import Manually Curated Judgements
exe curl -s -X PUT "$OPENSEARCH_SERVER_URL/_plugins/_search_relevance/judgments" \
-H "Content-type: application/json" \
-d'{
    "name": "Imported Judgments",
    "description": "Judgments generated outside SRW",
    "type": "IMPORT_JUDGMENT",
    "judgmentRatings": [
        {
            "query": "red dress",
            "ratings": [
                {
                    "docId": "B077ZJXCTS",
                    "rating": "0.000"
                },
                {
                    "docId": "B071S6LTJJ",
                    "rating": "0.000"
                },
                {
                    "docId": "B01IDSPDJI",
                    "rating": "0.000"
                },
                {
                    "docId": "B07QRCGL3G",
                    "rating": "0.000"
                },
                {
                    "docId": "B074V6Q1DR",
                    "rating": "0.000"
                }
            ]
        },
        {
            "query": "blue jeans",
            "ratings": [
                {
                    "docId": "B07L9V4Y98",
                    "rating": "0.000"
                },
                {
                    "docId": "B01N0DSRJC",
                    "rating": "0.000"
                },
                {
                    "docId": "B001CRAWCQ",
                    "rating": "0.000"
                },
                {
                    "docId": "B075DGJZRM",
                    "rating": "0.000"
                },
                {
                    "docId": "B009ZD297U",
                    "rating": "0.000"
                }
            ]
        }
    ]
}'

IMPORTED_JUDGMENT_LIST_ID=`jq -r '.judgment_id' < RES`

echo
echo Upload ESCI Judgments 

exe curl -s -X PUT "$OPENSEARCH_SERVER_URL/_plugins/_search_relevance/judgments" \
-H "Content-type: application/json" \
--data-binary @../sample-data/search-relevance/esci_us_judgments.json



ESCI_JUDGMENT_LIST_ID=`jq -r '.judgment_id' < RES`

echo
echo Create PAIRWISE Experiment
exe curl -s -X PUT "$OPENSEARCH_SERVER_URL/_plugins/_search_relevance/experiments" \
-H "Content-type: application/json" \
-d"{
   	\"querySetId\": \"$QUERY_SET_MANUAL\",
   	\"searchConfigurationList\": [\"$SC_BASELINE\", \"$SC_CHALLENGER\"],
   	\"size\": 10,
   	\"type\": \"PAIRWISE_COMPARISON\"
   }"
   

EX_PAIRWISE=`jq -r '.experiment_id' < RES`

echo
echo Experiment id: $EX_PAIRWISE

echo
echo Show PAIRWISE Experiment
exe curl -s -X GET "$OPENSEARCH_SERVER_URL/_plugins/_search_relevance/experiments/$EX_PAIRWISE"

echo
echo Create POINTWISE Experiment

exe curl -s -X PUT "$OPENSEARCH_SERVER_URL/_plugins/_search_relevance/experiments" \
-H "Content-type: application/json" \
-d"{
   	\"querySetId\": \"$QUERY_SET_MANUAL\",
   	\"searchConfigurationList\": [\"$SC_BASELINE\"],
    \"judgmentList\": [\"$IMPORTED_JUDGMENT_LIST_ID\"],
   	\"size\": 8,
   	\"type\": \"POINTWISE_EVALUATION\"
   }"

EX_POINTWISE=`jq -r '.experiment_id' < RES`

echo
echo Experiment id: $EX_POINTWISE
