port: 7880
log_level: info

rtc:
  tcp_port: 7881
  port_range_start: 50000
  port_range_end: 50020
  use_external_ip: true

keys:
  UMHKey1: op://${UMH_OP_VAULT}/LiveKit/api_secret

turn:
  enabled: true
  udp_port: 3478
