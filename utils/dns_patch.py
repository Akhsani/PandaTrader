import dns.resolver
import socket
import logging

logger = logging.getLogger(__name__)

# Cache for DNS lookups to avoid spamming the resolver
_dns_cache = {}

# Store original getaddrinfo before patching
_original_getaddrinfo = socket.getaddrinfo

def secure_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    """
    Custom getaddrinfo that resolves specific domains using Cloudflare 1.1.1.1 DNS.
    Everything else falls back to system DNS.
    """
    
    # List of domains to force DNS resolution for
    TARGET_DOMAINS = [
        'api.binance.com',
        'fapi.binance.com',
        'dapi.binance.com',
        'api1.binance.com',
        'api2.binance.com',
        'api3.binance.com',
        'data-api.binance.vision'
    ]

    # Check if host matches any target domain
    if host in TARGET_DOMAINS:
        if host in _dns_cache:
            ip = _dns_cache[host]
            # logger.info(f"Using cached IP {ip} for {host}")
        else:
            try:
                # Create a resolver that uses Cloudflare
                resolver = dns.resolver.Resolver()
                resolver.nameservers = ['1.1.1.1', '1.0.0.1']
                
                # Resolve A record (IPv4)
                answers = resolver.resolve(host, 'A')
                
                # Pick the first IP
                ip = answers[0].address
                _dns_cache[host] = ip
                print(f"🔒 Secure DNS (1.1.1.1): Resolved {host} -> {ip}")
            except Exception as e:
                print(f"⚠️ Secure DNS failed for {host}: {e}. Falling back to system DNS.")
                return _original_getaddrinfo(host, port, family, type, proto, flags)
        
        # Call original getaddrinfo with the IP address instead of hostname
        # This bypasses system DNS
        return _original_getaddrinfo(ip, port, family, type, proto, flags)

    # For all other hosts, use default system behavior
    return _original_getaddrinfo(host, port, family, type, proto, flags)

def apply_patch():
    """Apply the socket monkey patch"""
    socket.getaddrinfo = secure_getaddrinfo
    print("✅ DNS Patch applied: Binance API calls will use 1.1.1.1")

if __name__ == "__main__":
    # Test the patch
    apply_patch()
    try:
        # Simulate a request
        addr = socket.getaddrinfo("api.binance.com", 443)
        print(f"Result: {addr[0][4]}")
    except Exception as e:
        print(f"Test failed: {e}")
