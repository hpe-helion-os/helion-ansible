#monasca-notification
Installs the [monasca-notification](https://github.com/stackforge/monasca-notification) in a virtualenv.
Monasca Notification is part of the [Monasca](https://wiki.openstack.org/wiki/Monasca) project.

##Requirements
virtualenv must be installed.

- kafka_hosts - comma seperate list of kafka hosts
- mysql_host
- monasca_notification_mysql_user
- monasca_notification_mysql_password
- smtp_host
- zookeeper_hosts - comma seperate list of zookeeper hosts

Optionally if needed
- pip_index_url: Index URL to use instead of the default for installing pip packages
- smtp_user
- smtp_password
- notification_enable_email: Set to false to disable email notifications
- notification_enable_webhook: Set to false to disable webhook notifications
- notification_enable_pagerduty: Set to false to disable pagerduty notifications
- monasca_log_level: Log level for the Notification log, default to WARN
- mysql_ssl
  - This is a dictionary corresponding to the options in http://dev.mysql.com/doc/refman/5.0/en/mysql-ssl-set.html
  - For Example - {'ca':'/path/to/ca'}
- run_mode: One of Deploy, Stop, Install, Configure or Start. The default is Deploy which will do Install, Configure, then Start.

##Example Playbook

    hosts: monasca
    sudo: yes
    roles:
      - {role: tkuhlman.monasca-notification,
         monasca_notification_mysql_user: "{{notification_mysql_user}}",
         monasca_notification_mysql_password: "{{notification_mysql_password}}",
         tags: [notification]}

##License
Apache

##Author Information
Tim Kuhlman
Monasca Team email monasca@lists.launchpad.net
