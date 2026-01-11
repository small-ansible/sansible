# Copyright (c) 2024 Sansible Contributors
# MIT License

"""
Sansible Vault Support

Decrypt Ansible Vault encrypted files and strings.
Uses pure-Python cryptography for AES-256-CTR decryption.
"""

from __future__ import annotations

import binascii
import hashlib
import hmac
import os
import re
from pathlib import Path
from typing import Optional, Union

from sansible.engine.errors import VaultError


# Vault file header
VAULT_HEADER = "$ANSIBLE_VAULT"
VAULT_HEADER_REGEX = re.compile(r'^\$ANSIBLE_VAULT;(\d+\.\d+);(AES256)(?:;(\w+))?$')


class VaultSecret:
    """Represents a vault password/secret."""
    
    def __init__(self, password: Union[str, bytes]):
        if isinstance(password, str):
            self.password = password.encode('utf-8')
        else:
            self.password = password
    
    @classmethod
    def from_file(cls, password_file: Union[str, Path]) -> 'VaultSecret':
        """Load vault password from a file."""
        import sys
        
        path = Path(password_file)
        if not path.exists():
            raise VaultError(f"Vault password file not found: {path}")
        
        # Check if it's executable (password script)
        # On Unix: executable bit is set
        # On Windows: executable scripts not supported for vault passwords
        is_executable = os.access(path, os.X_OK) and sys.platform != 'win32'
        
        if is_executable:
            import subprocess
            try:
                result = subprocess.run(
                    [str(path)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if result.returncode != 0:
                    raise VaultError(f"Vault password script failed: {result.stderr}")
                password = result.stdout.strip()
            except subprocess.TimeoutExpired:
                raise VaultError("Vault password script timed out")
        else:
            password = path.read_text(encoding='utf-8').strip()
        
        return cls(password)


class VaultLib:
    """
    Ansible Vault decryption library.
    
    Supports AES256 encrypted content (the default and only format since Ansible 2.4).
    """
    
    def __init__(self, secrets: Optional[list[VaultSecret]] = None):
        self.secrets = secrets or []
    
    def add_secret(self, secret: VaultSecret) -> None:
        """Add a vault secret."""
        self.secrets.append(secret)
    
    def is_encrypted(self, data: Union[str, bytes]) -> bool:
        """Check if data is vault encrypted."""
        if isinstance(data, bytes):
            try:
                data = data.decode('utf-8')
            except UnicodeDecodeError:
                return False
        
        if not isinstance(data, str):
            return False
        
        return data.strip().startswith(VAULT_HEADER)
    
    def decrypt(self, data: Union[str, bytes], vault_id: Optional[str] = None) -> bytes:
        """
        Decrypt vault-encrypted data.
        
        Args:
            data: Vault encrypted content
            vault_id: Optional vault ID to use specific secret
            
        Returns:
            Decrypted content as bytes
        """
        if isinstance(data, bytes):
            data = data.decode('utf-8')
        
        if not isinstance(data, str):
            raise VaultError("Invalid vault data type")
        
        # Parse the vault envelope
        lines = data.strip().split('\n')
        if not lines:
            raise VaultError("Empty vault data")
        
        # Parse header
        header = lines[0]
        match = VAULT_HEADER_REGEX.match(header)
        if not match:
            raise VaultError(f"Invalid vault header: {header}")
        
        version = match.group(1)
        cipher = match.group(2)
        file_vault_id = match.group(3)
        
        if cipher != 'AES256':
            raise VaultError(f"Unsupported vault cipher: {cipher}")
        
        # Get the encrypted payload (hex encoded)
        payload_hex = ''.join(lines[1:]).replace('\n', '').replace(' ', '')
        
        try:
            payload = binascii.unhexlify(payload_hex)
        except binascii.Error as e:
            raise VaultError(f"Invalid vault payload: {e}")
        
        # Try each secret until one works
        for secret in self.secrets:
            try:
                return self._decrypt_aes256(payload, secret.password)
            except VaultError:
                continue
        
        raise VaultError("Vault decryption failed: no valid password found")
    
    def decrypt_file(self, file_path: Union[str, Path]) -> bytes:
        """Decrypt a vault-encrypted file."""
        path = Path(file_path)
        if not path.exists():
            raise VaultError(f"Vault file not found: {path}")
        
        content = path.read_text(encoding='utf-8')
        return self.decrypt(content)
    
    def _decrypt_aes256(self, payload: bytes, password: bytes) -> bytes:
        """
        Decrypt AES-256-CTR encrypted payload.
        
        The payload format is:
        - Salt (32 bytes, hex encoded = 64 chars)
        - HMAC (32 bytes, hex encoded = 64 chars)  
        - Ciphertext (remainder, hex encoded)
        
        All concatenated together before hex encoding.
        """
        # Payload is hex-encoded: salt + hmac + ciphertext
        try:
            payload_hex = payload.decode('utf-8')
        except UnicodeDecodeError:
            raise VaultError("Invalid vault payload encoding")
        
        # Split the components (each 64 hex chars = 32 bytes for salt and hmac)
        if len(payload_hex) < 128:  # At least salt + hmac
            raise VaultError("Vault payload too short")
        
        salt_hex = payload_hex[:64]
        hmac_hex = payload_hex[64:128]
        ciphertext_hex = payload_hex[128:]
        
        try:
            salt = binascii.unhexlify(salt_hex)
            expected_hmac = binascii.unhexlify(hmac_hex)
            ciphertext = binascii.unhexlify(ciphertext_hex)
        except binascii.Error as e:
            raise VaultError(f"Invalid vault data format: {e}")
        
        # Derive keys using PBKDF2
        # Ansible uses: key1 (32 bytes for AES), key2 (32 bytes for HMAC), iv (16 bytes)
        derived = self._pbkdf2_sha256(password, salt, 10000, 80)
        
        key = derived[:32]
        hmac_key = derived[32:64]
        iv = derived[64:80]
        
        # Verify HMAC
        computed_hmac = hmac.new(hmac_key, ciphertext, hashlib.sha256).digest()
        if not hmac.compare_digest(computed_hmac, expected_hmac):
            raise VaultError("HMAC verification failed - wrong password?")
        
        # Decrypt using AES-256-CTR
        plaintext = self._aes_ctr_decrypt(ciphertext, key, iv)
        
        # Remove PKCS7 padding
        plaintext = self._unpad_pkcs7(plaintext)
        
        return plaintext
    
    def _pbkdf2_sha256(self, password: bytes, salt: bytes, iterations: int, dklen: int) -> bytes:
        """PBKDF2-HMAC-SHA256 key derivation."""
        return hashlib.pbkdf2_hmac('sha256', password, salt, iterations, dklen)
    
    def _aes_ctr_decrypt(self, ciphertext: bytes, key: bytes, iv: bytes) -> bytes:
        """
        AES-256-CTR decryption.
        
        Pure Python implementation for portability.
        Falls back to cryptography library if available.
        """
        try:
            # Try using cryptography library (faster, more secure)
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.backends import default_backend
            
            cipher = Cipher(algorithms.AES(key), modes.CTR(iv), backend=default_backend())
            decryptor = cipher.decryptor()
            return decryptor.update(ciphertext) + decryptor.finalize()
        except ImportError:
            # Fall back to pure Python implementation
            return self._aes_ctr_decrypt_pure(ciphertext, key, iv)
    
    def _aes_ctr_decrypt_pure(self, ciphertext: bytes, key: bytes, iv: bytes) -> bytes:
        """Pure Python AES-CTR decryption (slow but portable)."""
        # This is a simplified implementation
        # For production, we strongly recommend installing cryptography
        try:
            # Try pyaes as fallback (optional dependency)
            import pyaes  # type: ignore[import-not-found]
            ctr = pyaes.AESModeOfOperationCTR(key, pyaes.Counter(int.from_bytes(iv, 'big')))
            return ctr.decrypt(ciphertext)
        except ImportError:
            raise VaultError(
                "Vault decryption requires either 'cryptography' or 'pyaes' package. "
                "Install with: pip install cryptography"
            )
    
    def _unpad_pkcs7(self, data: bytes) -> bytes:
        """Remove PKCS7 padding."""
        if not data:
            return data
        
        padding_len = data[-1]
        if padding_len > len(data) or padding_len > 16:
            # Invalid padding, return as-is
            return data
        
        # Verify padding
        if all(b == padding_len for b in data[-padding_len:]):
            return data[:-padding_len]
        
        return data


def decrypt_vault_string(encrypted: str, password: str) -> str:
    """Convenience function to decrypt a vault string."""
    vault = VaultLib([VaultSecret(password)])
    return vault.decrypt(encrypted).decode('utf-8')


def load_vault_file(file_path: Union[str, Path], password: str) -> str:
    """Convenience function to load and decrypt a vault file."""
    vault = VaultLib([VaultSecret(password)])
    return vault.decrypt_file(file_path).decode('utf-8')
