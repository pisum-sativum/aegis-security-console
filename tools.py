import requests
import json
import socket

# ==========================================
# AEGIS-AGENT: THE TOOL FACTORY
# ==========================================

# 🛡️ THE SAFETY LOCK
ALLOWED_TARGETS = ["127.0.0.1", "localhost"]


def network_recon(target_ip):
    """Scans the target for open ports."""
    print(f"\n[🔧 TOOL] Running Network Recon on {target_ip}...")
    

    import urllib.parse
    
    # Clean target_ip in case user inputs a URL or port
    if "://" in target_ip:
        target_ip = urllib.parse.urlparse(target_ip).hostname
    target_ip = target_ip.split(":")[0]

    open_ports = []
    ports_to_check = [80, 443, 5000, 5001, 8000, 8080]
    
    for port in ports_to_check:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((target_ip, port))
        if result == 0:
            open_ports.append(str(port))
        sock.close()
        
    if open_ports:
        return f"Recon Complete. Open ports found: {', '.join(open_ports)}"
    return "Recon Complete. No common web ports found open."

def local_directory_mapper(base_url):
    """A local-only directory discovery tool to map the API surface."""
    print(f"[🔧 TOOL] Running Local Directory Mapper on {base_url}...")
    
   
    # A small dictionary for our educational API
    common_paths = [
        "api", "api/v1", "docs", "swagger", "openapi.json", 
        "users", "users/v1", "users/v1/_debug", "admin", "login"
    ]
    
    found_endpoints = []
    if not base_url.endswith('/'):
        base_url += '/'
        
    for path in common_paths:
        target = base_url + path
        try:
            resp = requests.get(target, timeout=2)
            if resp.status_code != 404:
                found_endpoints.append(f"/{path} (Status: {resp.status_code})")
        except requests.exceptions.RequestException:
            pass
            
    if found_endpoints:
        return f"Mapping Complete. Found endpoints: {', '.join(found_endpoints)}"
    return "Mapping Complete. No common endpoints found."

def parse_api_schema(schema_url):
    """Downloads and parses an OpenAPI/Swagger JSON file to extract all valid routes."""
    print(f"[🔧 TOOL] Extracting API Schema from {schema_url}...")
    
   
    try: 
        resp = requests.get(schema_url, timeout=5)
        if resp.status_code != 200:
            return f"Failed to fetch schema. Status: {resp.status_code}"
            
        schema_data = resp.json()
        paths = schema_data.get("paths", {})
        
        if not paths:
            return "Schema found, but no paths were defined."
            
        extracted_routes = []
        for path, methods in paths.items():
            allowed_methods = [method.upper() for method in methods.keys()]
            extracted_routes.append(f"Path: {path} | Methods: {', '.join(allowed_methods)}")
            
        summary = "\n".join(extracted_routes)[:1500] 
        return f"✅ Schema Parsed Successfully. Discovered Routes:\n{summary}"
        
    except json.JSONDecodeError:
        return "ERROR: The file found is not valid JSON."
    except Exception as e:
        return f"Schema extraction failed: {str(e)}"

def universal_http_client(method, url, payload=None, headers=None):
    """A generic client that lets the AI send ANY web request."""
    print(f"[🔧 TOOL] Sending {method} request to {url}...")
    
   
    try:
        if isinstance(payload, str) and payload != "":
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                pass 

        if isinstance(headers, str) and headers != "":
            try:
                headers = json.loads(headers)
            except json.JSONDecodeError:
                headers = {}

        if headers is None:
            headers = {}

        if method.upper() == "GET":
            resp = requests.get(url, headers=headers, timeout=5)
        elif method.upper() == "POST":
            resp = requests.post(url, json=payload, headers=headers, timeout=5)
        elif method.upper() == "PUT":
            resp = requests.put(url, json=payload, headers=headers, timeout=5)
        elif method.upper() == "DELETE":
            resp = requests.delete(url, headers=headers, timeout=5)
        else:
            return f"ERROR: Unsupported HTTP method '{method}'"
            
        return f"Status: {resp.status_code} | Body: {resp.text[:300]}..."
    except Exception as e:
        return f"HTTP Request Failed: {str(e)}"