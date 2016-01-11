#monasca-thresh
Installs the [monasca-thresh](https://github.com/stackforge/monasca-notification) part of the [Monasca](https://wiki.openstack.org/wiki/Monasca) project.
Monasca-thresh requires storm to be running and should be installed on the nimbus box.

##Requirements
- kafka_hosts - comma separated list of host:port pairs.
- mysql_host - By default ssl will be used if available.
- monasca_thresh_mysql_user
- monasca_thresh_mysql_password
- zookeeper_hosts - comma separated list of host:port pairs.

## Optional
- run_mode: One of Deploy, Stop, Install, Configure or Start. The default is Deploy which will do Install, Configure, then Start.

##License
Apache

##Author Information
Tim Kuhlman
Monasca Team email monasca@lists.launchpad.net
