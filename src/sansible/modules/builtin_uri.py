"""
Sansible uri module

Interact with HTTP/HTTPS web services.
"""

import json
import urllib.request
import urllib.error
import urllib.parse
import ssl
from typing import Any, Dict, Optional

from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class UriModule(Module):
    """
    Interact with HTTP/HTTPS web services.
    
    Sends HTTP requests and returns results.
    """
    
    name = "uri"
    required_args = ["url"]
    optional_args = {
        "method": "GET",
        "body": None,
        "body_format": "raw",       # raw, json, form-urlencoded
        "headers": {},
        "status_code": [200],       # Expected status codes
        "return_content": False,
        "timeout": 30,
        "validate_certs": True,
        "follow_redirects": "safe",  # all, safe, none
        "user": None,
        "password": None,
        "force_basic_auth": False,
    }
    
    async def run(self) -> ModuleResult:
        """Make the HTTP request."""
        url = self.args["url"]
        method = self.get_arg("method", "GET").upper()
        body = self.get_arg("body")
        body_format = self.get_arg("body_format", "raw")
        headers = self.get_arg("headers", {})
        expected_status = self.get_arg("status_code", [200])
        timeout = self.get_arg("timeout", 30)
        validate_certs = self.get_arg("validate_certs", True)
        
        if isinstance(expected_status, int):
            expected_status = [expected_status]
        
        if self.context.check_mode:
            return ModuleResult(
                changed=False,
                msg=f"Would make {method} request to {url} (check mode)",
            )
        
        # Prepare request body
        data = None
        if body:
            if body_format == "json":
                if isinstance(body, dict):
                    data = json.dumps(body).encode("utf-8")
                else:
                    data = body.encode("utf-8")
                headers.setdefault("Content-Type", "application/json")
            elif body_format == "form-urlencoded":
                if isinstance(body, dict):
                    data = urllib.parse.urlencode(body).encode("utf-8")
                else:
                    data = body.encode("utf-8")
                headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
            else:
                data = body.encode("utf-8") if isinstance(body, str) else body
        
        # Build request
        request = urllib.request.Request(url, data=data, method=method)
        
        for key, value in headers.items():
            request.add_header(key, value)
        
        # Handle basic auth
        user = self.get_arg("user")
        password = self.get_arg("password")
        if user and password:
            import base64
            credentials = base64.b64encode(f"{user}:{password}".encode()).decode()
            request.add_header("Authorization", f"Basic {credentials}")
        
        # SSL context
        ssl_context = None
        if not validate_certs:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
        
        try:
            with urllib.request.urlopen(request, timeout=timeout, context=ssl_context) as response:
                status = response.getcode()
                response_headers = dict(response.headers)
                content = response.read().decode("utf-8", errors="replace")
                
                # Check status code
                if status not in expected_status:
                    return ModuleResult(
                        failed=True,
                        msg=f"Status code {status} not in expected list {expected_status}",
                        results={
                            "status": status,
                            "url": url,
                            "content": content if self.get_arg("return_content") else "",
                        },
                    )
                
                result_data: Dict[str, Any] = {
                    "status": status,
                    "url": url,
                    "msg": "OK",
                    "redirected": False,
                    "elapsed": 0,
                }
                
                if self.get_arg("return_content"):
                    result_data["content"] = content
                    # Try to parse JSON
                    try:
                        result_data["json"] = json.loads(content)
                    except (json.JSONDecodeError, ValueError):
                        pass
                
                return ModuleResult(
                    changed=method not in ("GET", "HEAD"),
                    msg=f"{method} {url} returned {status}",
                    results=result_data,
                )
                
        except urllib.error.HTTPError as e:
            status = e.code
            content = e.read().decode("utf-8", errors="replace") if e.fp else ""
            
            if status in expected_status:
                return ModuleResult(
                    changed=method not in ("GET", "HEAD"),
                    msg=f"{method} {url} returned {status}",
                    results={
                        "status": status,
                        "url": url,
                        "content": content if self.get_arg("return_content") else "",
                    },
                )
            
            return ModuleResult(
                failed=True,
                msg=f"HTTP error {status}: {e.reason}",
                results={"status": status, "url": url},
            )
        except urllib.error.URLError as e:
            return ModuleResult(
                failed=True,
                msg=f"Failed to connect to {url}: {e.reason}",
            )
        except Exception as e:
            return ModuleResult(
                failed=True,
                msg=f"Request failed: {str(e)}",
            )


@register_module
class GetUrlModule(Module):
    """
    Download files from HTTP/HTTPS/FTP.
    
    Downloads a file to a remote machine.
    """
    
    name = "get_url"
    required_args = ["url", "dest"]
    optional_args = {
        "mode": None,
        "owner": None,
        "group": None,
        "force": False,         # Download even if file exists
        "checksum": None,       # Checksum to verify
        "timeout": 30,
        "validate_certs": True,
        "headers": {},
        "url_username": None,
        "url_password": None,
    }
    
    async def run(self) -> ModuleResult:
        """Download the file."""
        url = self.args["url"]
        dest = self.args["dest"]
        force = self.get_arg("force", False)
        
        if self.context.check_mode:
            return ModuleResult(
                changed=True,
                msg=f"Would download {url} to {dest} (check mode)",
            )
        
        # Check if file exists
        if not force:
            stat_result = await self.connection.stat(dest)
            if stat_result and stat_result.get("exists"):
                return ModuleResult(
                    changed=False,
                    msg=f"File already exists at {dest}",
                    results={"dest": dest},
                )
        
        # Download to local temp file first, then upload
        import tempfile
        import os
        
        timeout = self.get_arg("timeout", 30)
        validate_certs = self.get_arg("validate_certs", True)
        headers = self.get_arg("headers", {})
        
        # Build request
        request = urllib.request.Request(url)
        for key, value in headers.items():
            request.add_header(key, value)
        
        # Handle auth
        user = self.get_arg("url_username")
        password = self.get_arg("url_password")
        if user and password:
            import base64
            credentials = base64.b64encode(f"{user}:{password}".encode()).decode()
            request.add_header("Authorization", f"Basic {credentials}")
        
        # SSL context
        ssl_context = None
        if not validate_certs:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
        
        try:
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                tmp_path = tmp_file.name
                
                with urllib.request.urlopen(request, timeout=timeout, context=ssl_context) as response:
                    tmp_file.write(response.read())
            
            # Verify checksum if provided
            checksum = self.get_arg("checksum")
            if checksum:
                import hashlib
                algo, expected = checksum.split(":", 1) if ":" in checksum else ("sha256", checksum)
                with open(tmp_path, "rb") as f:
                    actual = hashlib.new(algo, f.read()).hexdigest()
                if actual != expected:
                    os.unlink(tmp_path)
                    return ModuleResult(
                        failed=True,
                        msg=f"Checksum mismatch: expected {expected}, got {actual}",
                    )
            
            # Upload to remote
            await self.connection.put(tmp_path, dest)
            os.unlink(tmp_path)
            
            # Set permissions
            mode = self.get_arg("mode")
            if mode:
                cmd = f"chmod {mode} {dest}"
                cmd = self.wrap_become(cmd)
                await self.connection.run(cmd)
            
            owner = self.get_arg("owner")
            group = self.get_arg("group")
            if owner or group:
                ownership = f"{owner or ''}:{group or ''}" if group else owner
                cmd = f"chown {ownership} {dest}"
                cmd = self.wrap_become(cmd)
                await self.connection.run(cmd)
            
            return ModuleResult(
                changed=True,
                msg=f"Downloaded {url} to {dest}",
                results={"dest": dest, "url": url},
            )
            
        except urllib.error.URLError as e:
            return ModuleResult(
                failed=True,
                msg=f"Failed to download {url}: {e.reason}",
            )
        except Exception as e:
            return ModuleResult(
                failed=True,
                msg=f"Download failed: {str(e)}",
            )
