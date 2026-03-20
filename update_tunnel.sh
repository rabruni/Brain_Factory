#!/bin/bash
# Update Cloudflare tunnel config — all DoPeJarMo services
# Run: sudo bash ~/Cowork/Brain_Factory/update_tunnel.sh

set -e

cat > /etc/cloudflared/config.yml << 'EOF'
# Cloudflare Tunnel config — updated 2026-03-19
tunnel: 42c0b125-d403-4fb2-a8f7-2a16f79dab02
credentials-file: /etc/cloudflared/42c0b125-d403-4fb2-a8f7-2a16f79dab02.json

ingress:
  - hostname: ssh.dopejarmo.com
    service: ssh://localhost:22
  - hostname: backstage.dopejarmo.com
    service: http://localhost:3000
    originRequest:
      httpHostHeader: localhost
  - hostname: backstage-api.dopejarmo.com
    service: http://localhost:7007
    originRequest:
      httpHostHeader: localhost
  - hostname: portal.dopejarmo.com
    service: http://localhost:8501
    originRequest:
      httpHostHeader: localhost
  - hostname: mcp.dopejarmo.com
    service: http://localhost:8502
  - service: http_status:404
EOF

echo "Config written. Restarting tunnel..."
launchctl kickstart -k system/com.cloudflare.cloudflared
echo "Done. Services:"
echo "  portal.dopejarmo.com     → Streamlit portal (:8501)"
echo "  mcp.dopejarmo.com        → MCP HTTP API (:8502)"
echo "  backstage.dopejarmo.com  → Backstage UI (:3000)"
echo "  backstage-api.dopejarmo.com → Backstage API (:7007)"
