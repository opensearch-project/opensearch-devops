# OpenSearch Nightly Playground
Get a glance of your work in action on a fully deployed distribution cluster for upcoming version of OpenSearch and OpenSearch-Dashboards. The purpose of this playground is to get early feedback on upcoming features and see it in action.
This cluster will deploy nightly build artifacts daily at 00:00 UTC (5PM PST).

* **Where can I access it?**\
  https://playground.nightly.opensearch.org/

* **Which commit was used to build this distribution?**\
  Every user by default has the read-only access to these clusters. The entire distribution manifest of the deployed artifact is indexed in the cluster as a part of the automation. Simply go to the `dev-tools` page and run the below query:
  ```
  GET opensearch/_doc/1
  GET opensearch-dashboards/_doc/1
  ```
  This will give you components present in the deployed cluster along with the commit_id and the artifact location.

* **Component missing from the cluster/distribution?**\
  If a component is missing from the distribution, most likely it failed to build and hence was not able to make the cut into the nightly distribution artifact. Please visit the corresponding component repository and search for build failure autocut issues. Example: https://github.com/opensearch-project/security-analytics/issues/904

* **What if I need more data indexed into these cluster?**\
  Please feel free to raise an issue or pull request with the required data that you need in these clusters. The maintainers will review the data for security and sensitive information.

* **What if I need more permissions to test different features on these clusters?**\
  Please create a GitHub issue to request for permissions with your GitHub username.
