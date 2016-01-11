# InfluxDB

Install [InfluxDB](http://influxdb.org/) time series database

## Role Variables

| Name                        | Default Value | Description                                                      |
|-----------------------------|---------------|------------------------------------------------------------------|
| influxdb_client_port        | 8086          | The port for influxdb client connections                         |
| influxdb_ssl_certificate    | None          | If defined the influxdb_client_port will be set to SSL           |
| influxdb_ssl_certificate_src| None          | If defined the file at this location wil be copied to the host   |
| influxdb_use_apt            | false         | If true apt will be used to install influxdb                     |
| influxdb_deb_src_url        | http://s3.amazonaws.com/influxdb/ | If not using apt the url base to pull the deb from |


##Optional
- run_mode - One of Deploy, Stop, Install, Start, or Use. The default is Deploy which will do Install, Configure, then Start.

### Clustering
To enable clustering define `influxdb_peers` on all nodes.
`influxdb_peers` is a list of `host:port` entries, one for each node.

## License

MIT
