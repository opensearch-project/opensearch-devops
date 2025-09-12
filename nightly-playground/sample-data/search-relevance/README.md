This directory contains:

1) Product data extracted from the ESCI ecommerce dataset and formatted for bulk loading into OpenSearch.  `esci_us_opensearch_shrunk.ndjson`.   Created using the scripts in ./data-prep/ directory against the original ESCI dataset sourced from https://esci-s.s3.amazonaws.com/esci.json.zst.

2) Queries and events in the UBI format sourced from the ESCI data set in `ubi_queries_events.ndjson`. Created using https://github.com/opensearch-project/user-behavior-insights/tree/main/ubi-data-generator.

3) Queries (`esci_us_queryset.json`) and matching Judgments (`esci_us_judgments.json`) sourced from the ESCI data set.

https://github.com/amazon-science/esci-data

@article{reddy2022shopping,
title={Shopping Queries Dataset: A Large-Scale {ESCI} Benchmark for Improving Product Search},
author={Chandan K. Reddy and Lluís Màrquez and Fran Valero and Nikhil Rao and Hugo Zaragoza and Sambaran Bandyopadhyay and Arnab Biswas and Anlu Xing and Karthik Subbian},
year={2022},
eprint={2206.06588},
archivePrefix={arXiv}
}
