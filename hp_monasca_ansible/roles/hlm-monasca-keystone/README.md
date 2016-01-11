#HLM Monasca Keystone
Performs some Keystone setup for Monasca in HLM.
This role adds one or more users/projects/roles to Keystone, as specified in mon_keystone_users:

```
mon_keystone_users:
  - username: monasca-agent
    password: some-password
    project: some-project
    role: monasca-agent
```
It also creates a Monasca endpoint in keystone.

Keystone Authentication:
Configure by setting `keystone_admin`, `keystone_admin_password`, and `keystone_admin_project`

##Requirements
- Server running OpenStack Keystone
- Hostname or IP of Monasca API server

##Optional

##License
Apache

##Author Information
Ryan Brandt

Monasca Team email monasca@lists.launchpad.net
