README
======

This repo contains the following roles:
- COBBLER: Cobbler server role

The verbs:
- configure
- install
- start
- populate

The operations:
- deploy

Repo structure:

```
├── bm-reimage.yml
├── cobbler-bm-verify.yml
├── cobbler-deploy.yml
├── cobbler-power-down.yml
├── cobbler-power-status.yml
├── cobbler-power-up.yml
├── cobbler-provision.yml
├── cobbler-set-diskboot-all.yml
├── cobbler-set-pxeboot-all.yml
├── cobbler-wait-for-shutdown.yml
├── cobbler-wait-for-ssh.yml
├── library
│   ├── bmconfig
│   └── ipmi
├── README.md
└── roles
    └── cobbler
        ├── defaults
        │   └── main.yml
        ├── files
        │   ├── cobbler.conf
        │   ├── configure_network.sh
        │   ├── fence_ipmilan.template
        │   └── validate_yaml
        ├── tasks
        │   ├── check-ipmi-connectivity.yml
        │   ├── configure.yml
        │   ├── get-nodelist.yml
        │   ├── install.yml
        │   ├── populate.yml
        │   ├── power-cycle-all.yml
        │   ├── power-down-all.yml
        │   ├── power-up-all.yml
        │   ├── set-diskboot-all.yml
        │   ├── set-pxeboot-all.yml
        │   ├── set-vars.yml
        │   ├── start.yml
        │   ├── verify-bm-install.yml
        │   ├── wait-for-shutdown.yml
        │   └── wait-for-ssh.yml
        ├── templates
        │   ├── cobbler.dhcp.template.j2
        │   ├── dhcpd.conf.j2
        │   ├── grub.cfg.j2
        │   ├── hlinux-server-vm.preseed.j2
        │   ├── isc-dhcp-server.j2
        │   └── settings.j2
        └── vars
            └── main.yml
```
