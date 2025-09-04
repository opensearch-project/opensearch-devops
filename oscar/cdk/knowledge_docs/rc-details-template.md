## See OpenSearch RC $OPENSEARCH_RC_NUMBER and OpenSearch-Dashboards RC $OPENSEARCH_DASHBOARDS_RC_NUMBER details
<details><summary>OpenSearch $OPENSEARCH_RC_NUMBER and OpenSearch-Dashboards $OPENSEARCH_DASHBOARDS_RC_NUMBER details</summary>
<p>
 ## OpenSearch $OPENSEARCH_RC_BUILD_NUMBER and OpenSearch-Dashboards $OPENSEARCH_DASHBOARDS_RC_BUILD_NUMBER is ready for your test.

OpenSearch - [Build $OPENSEARCH_RC_BUILD_NUMBER](https://build.ci.opensearch.org/blue/organizations/jenkins/distribution-build-opensearch/detail/distribution-build-opensearch/$OPENSEARCH_RC_BUILD_NUMBER/pipeline)
OpenSearch Dashboards - [Build $OPENSEARCH_DASHBOARDS_RC_BUILD_NUMBER](https://build.ci.opensearch.org/blue/organizations/jenkins/distribution-build-opensearch-dashboards/detail/distribution-build-opensearch-dashboards/$OPENSEARCH_DASHBOARDS_RC_BUILD_NUMBER/pipeline)

- Use the following Docker-Compose to setup a cluster
  <details><summary>docker-compose.yml</summary>
  <p>
    <pre>
    <code>
  version: '3'
  services:
    opensearch-node1:
      image: opensearchstaging/opensearch:$VERSION.$OPENSEARCH_RC_BUILD_NUMBER
      container_name: opensearch-node1
      environment:
        - cluster.name=opensearch-cluster
        - node.name=opensearch-node1
        - discovery.seed_hosts=opensearch-node1,opensearch-node2
        - cluster.initial_cluster_manager_nodes=opensearch-node1,opensearch-node2
        - bootstrap.memory_lock=true # along with the memlock settings below, disables swapping
        - OPENSEARCH_INITIAL_ADMIN_PASSWORD=myStrongPassword123!
      ulimits:
        memlock:
          soft: -1
          hard: -1
        nofile:
          soft: 65536 # maximum number of open files for the OpenSearch user, set to at least 65536 on modern systems
          hard: 65536
      volumes:
        - opensearch-data1:/usr/share/opensearch/data
      ports:
        - 9200:9200
        - 9600:9600 # required for Performance Analyzer
      networks:
        - opensearch-net
    opensearch-node2:
      image: opensearchstaging/opensearch:$VERSION.$OPENSEARCH_RC_BUILD_NUMBER
      container_name: opensearch-node2
      environment:
        - cluster.name=opensearch-cluster
        - node.name=opensearch-node2
        - discovery.seed_hosts=opensearch-node1,opensearch-node2
        - cluster.initial_cluster_manager_nodes=opensearch-node1,opensearch-node2
        - bootstrap.memory_lock=true
        - OPENSEARCH_INITIAL_ADMIN_PASSWORD=myStrongPassword123!
      ulimits:
        memlock:
          soft: -1
          hard: -1
        nofile:
          soft: 65536
          hard: 65536
      volumes:
        - opensearch-data2:/usr/share/opensearch/data
      networks:
        - opensearch-net
    opensearch-dashboards:
      image: opensearchstaging/opensearch-dashboards:$VERSION.$OPENSEARCH_DASHBOARDS_RC_BUILD_NUMBER
      container_name: opensearch-dashboards
      ports:
        - 5601:5601
      expose:
        - "5601"
      environment:
        OPENSEARCH_HOSTS: '["https://opensearch-node1:9200","https://opensearch-node2:9200"]'
      networks:
        - opensearch-net
  volumes:
    opensearch-data1:
    opensearch-data2:

  networks:
  opensearch-net:
  </code>
  </pre>

  </p>
  </details>

    + Download the above docker-compose.yml on your machine.
    + Get latest image versions `docker-compose pull`.
    + Start the cluster `docker-compose up`.

- [OpenSearch docker $VERSION.$OPENSEARCH_RC_BUILD_NUMBER](https://hub.docker.com/r/opensearchstaging/opensearch/tags?page=1&name=$VERSION.$OPENSEARCH_RC_BUILD_NUMBER)
    + Start without security
        - Docker command `docker pull opensearchstaging/opensearch:$VERSION.$OPENSEARCH_RC_BUILD_NUMBER && docker run -it -p 9200:9200 -e "discovery.type=single-node" -e "DISABLE_SECURITY_PLUGIN=true" opensearchstaging/opensearch:$VERSION.$OPENSEARCH_RC_BUILD_NUMBER`
        - Connect command `curl http://localhost:9200/`
    + Start with security
        - Docker command
      ```
      docker pull opensearchstaging/opensearch:$VERSION.$OPENSEARCH_RC_BUILD_NUMBER && docker run -it -p 9200:9200 -e "discovery.type=single-node" -e "OPENSEARCH_INITIAL_ADMIN_PASSWORD=myStrongPassword123!" opensearchstaging/opensearch:$VERSION.$OPENSEARCH_RC_BUILD_NUMBER
      ```
        - Connect command `curl --insecure 'https://admin:myStrongPassword123!@localhost:9200/'`
- [OpenSearch-Dashboards docker $VERSION.$OPENSEARCH_DASHBOARDS_RC_BUILD_NUMBER](https://hub.docker.com/r/opensearchstaging/opensearch-dashboards/tags?page=1&name=$VERSION.$OPENSEARCH_DASHBOARDS_RC_BUILD_NUMBER)
    + Start without security
        - Docker command `docker pull opensearchstaging/opensearch-dashboards:$VERSION.$OPENSEARCH_DASHBOARDS_RC_BUILD_NUMBER && docker run -it --network="host" -e "DISABLE_SECURITY_DASHBOARDS_PLUGIN=true" opensearchstaging/opensearch-dashboards:$VERSION.$OPENSEARCH_DASHBOARDS_RC_BUILD_NUMBER`
        - URL `http://localhost:5601/`
    + Start with security
        - Docker command `docker pull opensearchstaging/opensearch-dashboards:$VERSION.$OPENSEARCH_DASHBOARDS_RC_BUILD_NUMBER && docker run -it --network="host" opensearchstaging/opensearch-dashboards:$VERSION.$OPENSEARCH_DASHBOARDS_RC_BUILD_NUMBER`
        - URL `http://localhost:5601/`

- Use TARs to deploy OpenSearch Manually
    + OpenSearch - Build $OPENSEARCH_RC_BUILD_NUMBER (Note: Windows version does not have performance analyzer plugin)
        * arm64 [[manifest](https://ci.opensearch.org/ci/dbc/distribution-build-opensearch/$VERSION/$OPENSEARCH_RC_BUILD_NUMBER/linux/arm64/tar/dist/opensearch/manifest.yml)] [[tar](https://ci.opensearch.org/ci/dbc/distribution-build-opensearch/$VERSION/$OPENSEARCH_RC_BUILD_NUMBER/linux/arm64/tar/dist/opensearch/opensearch-$VERSION-linux-arm64.tar.gz)] [[rpm](https://ci.opensearch.org/ci/dbc/distribution-build-opensearch/$VERSION/$OPENSEARCH_RC_BUILD_NUMBER/linux/arm64/rpm/dist/opensearch/opensearch-$VERSION-linux-arm64.rpm)][[deb](https://ci.opensearch.org/ci/dbc/distribution-build-opensearch/$VERSION/$OPENSEARCH_RC_BUILD_NUMBER/linux/arm64/deb/dist/opensearch/opensearch-$VERSION-linux-arm64.deb)]
        * x64 [[manifest](https://ci.opensearch.org/ci/dbc/distribution-build-opensearch/$VERSION/$OPENSEARCH_RC_BUILD_NUMBER/linux/x64/tar/dist/opensearch/manifest.yml)] [[tar](https://ci.opensearch.org/ci/dbc/distribution-build-opensearch/$VERSION/$OPENSEARCH_RC_BUILD_NUMBER/linux/x64/tar/dist/opensearch/opensearch-$VERSION-linux-x64.tar.gz)] [[rpm](https://ci.opensearch.org/ci/dbc/distribution-build-opensearch/$VERSION/$OPENSEARCH_RC_BUILD_NUMBER/linux/x64/rpm/dist/opensearch/opensearch-$VERSION-linux-x64.rpm)] [[deb](https://ci.opensearch.org/ci/dbc/distribution-build-opensearch/$VERSION/$OPENSEARCH_RC_BUILD_NUMBER/linux/x64/deb/dist/opensearch/opensearch-$VERSION-linux-x64.deb)] [[windows](https://ci.opensearch.org/ci/dbc/distribution-build-opensearch/$VERSION/$OPENSEARCH_RC_BUILD_NUMBER/windows/x64/zip/dist/opensearch/opensearch-$VERSION-windows-x64.zip)]


+ OpenSearch Dashboards - Build $OPENSEARCH_DASHBOARDS_RC_BUILD_NUMBER
    * arm64 [[manifest](https://ci.opensearch.org/ci/dbc/distribution-build-opensearch-dashboards/$VERSION/$OPENSEARCH_DASHBOARDS_RC_BUILD_NUMBER/linux/arm64/tar/dist/opensearch-dashboards/manifest.yml)] [[tar](https://ci.opensearch.org/ci/dbc/distribution-build-opensearch-dashboards/$VERSION/$OPENSEARCH_DASHBOARDS_RC_BUILD_NUMBER/linux/arm64/tar/dist/opensearch-dashboards/opensearch-dashboards-$VERSION-linux-arm64.tar.gz)][[rpm](https://ci.opensearch.org/ci/dbc/distribution-build-opensearch-dashboards/$VERSION/$OPENSEARCH_DASHBOARDS_RC_BUILD_NUMBER/linux/arm64/rpm/dist/opensearch-dashboards/opensearch-dashboards-$VERSION-linux-arm64.rpm)][[deb](https://ci.opensearch.org/ci/dbc/distribution-build-opensearch-dashboards/$VERSION/$OPENSEARCH_DASHBOARDS_RC_BUILD_NUMBER/linux/arm64/deb/dist/opensearch-dashboards/opensearch-dashboards-$VERSION-linux-arm64.deb)]
    * x64 [[manifest](https://ci.opensearch.org/ci/dbc/distribution-build-opensearch-dashboards/$VERSION/$OPENSEARCH_DASHBOARDS_RC_BUILD_NUMBER/linux/x64/tar/dist/opensearch-dashboards/manifest.yml)] [[tar](https://ci.opensearch.org/ci/dbc/distribution-build-opensearch-dashboards/$VERSION/$OPENSEARCH_DASHBOARDS_RC_BUILD_NUMBER/linux/x64/tar/dist/opensearch-dashboards/opensearch-dashboards-$VERSION-linux-x64.tar.gz)][[rpm](https://ci.opensearch.org/ci/dbc/distribution-build-opensearch-dashboards/$VERSION/$OPENSEARCH_DASHBOARDS_RC_BUILD_NUMBER/linux/x64/rpm/dist/opensearch-dashboards/opensearch-dashboards-$VERSION-linux-x64.rpm)] [[deb](https://ci.opensearch.org/ci/dbc/distribution-build-opensearch-dashboards/$VERSION/$OPENSEARCH_DASHBOARDS_RC_BUILD_NUMBER/linux/x64/deb/dist/opensearch-dashboards/opensearch-dashboards-$VERSION-linux-x64.deb)] [[windows](https://ci.opensearch.org/ci/dbc/distribution-build-opensearch-dashboards/$VERSION/$OPENSEARCH_DASHBOARDS_RC_BUILD_NUMBER/windows/x64/zip/dist/opensearch-dashboards/opensearch-dashboards-$VERSION-windows-x64.zip)]


_Check how to install [opensearch](https://opensearch.org/docs/latest/install-and-configure/install-opensearch/index/) and [dashboards](https://opensearch.org/docs/latest/install-and-configure/install-dashboards/index/) on different platforms_

## Integration Test Results

- Use the https://metrics.opensearch.org/_dashboards/goto/9ed74dd90eb31c7b83f3542e43328088?security_tenant=global.

- Filter by the `distribution_build_number`. Use **$OPENSEARCH_RC_BUILD_NUMBER** for OpenSearch and **$OPENSEARCH_DASHBOARDS_RC_BUILD_NUMBER** for OpenSearch Dashboards.
  Example when filtered with **$OPENSEARCH_RC_BUILD_NUMBER** we can see all the passed/failed OpenSearch components. Check the metrics [here](https://metrics.opensearch.org/_dashboards/app/dashboards#/view/21aad140-49f6-11ef-bbdd-39a9b324a5aa?_g=(filters:!(),refreshInterval:(pause:!t,value:0),time:(from:now%2Fw,to:now%2Fw))&_a=(description:'OpenSearch%20Release%20Build%20and%20Integration%20Test%20Results',filters:!(('\$state':(store:appState),meta:(alias:!n,controlledBy:'1721852613904',disabled:!f,index:'16f55f10-4977-11ef-8565-15a1562cd0a0',key:version,negate:!f,params:(query:'$VERSION'),type:phrase),query:(match_phrase:(version:'$VERSION'))),('\$state':(store:appState),meta:(alias:!n,disabled:!f,index:'23eb6520-4977-11ef-bbdd-39a9b324a5aa',key:distribution_build_number,negate:!f,params:!('$OPENSEARCH_RC_BUILD_NUMBER','%20$OPENSEARCH_DASHBOARDS_RC_BUILD_NUMBER'),type:phrases,value:'$OPENSEARCH_RC_BUILD_NUMBER,%20%20$OPENSEARCH_DASHBOARDS_RC_BUILD_NUMBER'),query:(bool:(minimum_should_match:1,should:!((match_phrase:(distribution_build_number:'$OPENSEARCH_RC_BUILD_NUMBER')),(match_phrase:(distribution_build_number:'%20$OPENSEARCH_DASHBOARDS_RC_BUILD_NUMBER')))))),('\$state':(store:appState),meta:(alias:!n,controlledBy:'1722482131538',disabled:!f,index:'16f55f10-4977-11ef-8565-15a1562cd0a0',key:rc_number,negate:!f,params:(query:4),type:phrase),query:(match_phrase:(rc_number:4)))),fullScreenMode:!f,options:(hidePanelTitles:!f,useMargins:!t),query:(language:kuery,query:''),timeRestore:!t,title:'OpenSearch%20Release%20Build%20and%20Integration%20Test%20Results',viewMode:view)).

- Find the list of the created **AUTOCUT** issues here https://github.com/issues?page=1&q=is%3Aopen+is%3Aissue+user%3Aopensearch-project+label%3Av$VERSION+label%3Aautocut+%5BAUTOCUT%5D+in%3Atitle.

Thank you
</p>
</details>


<details><summary>OpenSearch Docker-Scan Results</summary>
<p>

[Workflow run]($OPENSEARCH_DOCKER_SCAN_URL)
<pre>
<code>

$OPENSEARCH_DOCKER_SCAN_RESULTS

</code>
</pre>
</p>
</details>

<details><summary>OpenSearch-Dashboards Docker-Scan Results</summary>
<p>

[Workflow run]($OPENSEARCH_DASHBOARDS_DOCKER_SCAN_URL)
<pre>
<code>

$OPENSEARCH_DASHBOARDS_DOCKER_SCAN_RESULTS

</code>
</pre>
</p>
</details>
