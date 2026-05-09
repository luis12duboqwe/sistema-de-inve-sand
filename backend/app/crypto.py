"""
Utilidades de cifrado para tokens y credenciales sensibles.

Proporciona funciones para encriptar/desencriptar tokens de canal.
Los tokens se almacenan en la BD de forma encriptada en producción.

Uso:
    from app.crypto import encrypt_token, decrypt_token
    
    # Guardar
    encrypted = encrypt_token("EAA...BCXYZ")
    profile.access_token = encrypted
    
    # Usar
    token = decrypt_token(profile.access_token)
    api_call(token=token)
"""

import os
from cryptography.fernet import Fernet
import logging

logger = logging.getLogger(__name__)


class TokenCryptoManager:
    """Gestor de cifrado/descifrado de tokens sensibles."""

    def __init__(self):
        """Inicializa el gestor con clave del entorno o genera una dev."""
        self.encryption_key = self._get_or_create_key()
        if self.encryption_key == b"dev_unencrypted_key":
            self.cipher = None
            self.encrypted = False
            return

        try:
            self.cipher = Fernet(self.encryption_key)
            self.encrypted = self.encryption_key != b"dev_unencrypted_key"
        except Exception as e:
            logger.error(f"Error inicializando cipher: {e}")
            self.encrypted = False
            self.cipher = None

    def _get_or_create_key(self) -> bytes:
        """
        Obtiene clave de entorno o retorna clave de desarrollo.
        
        En producción, debe existir CHANNEL_ENCRYPTION_KEY:
            CHANNEL_ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
        """
        key_str = os.getenv("CHANNEL_ENCRYPTION_KEY")
        environment = os.getenv("ENVIRONMENT", "").strip().lower()

        if not key_str or not environment:
            try:
                from app.config import settings

                key_str = key_str or settings.channel_encryption_key
                environment = environment or settings.environment
            except Exception:
                pass

        environment = (environment or "development").strip().lower()
        
        if key_str:
            try:
                key_bytes = key_str.encode()
                # Validar que sea una clave Fernet válida
                Fernet(key_bytes)
                return key_bytes
            except Exception as e:
                logger.error(f"CHANNEL_ENCRYPTION_KEY inválido: {e}")
                if environment == "production":
                    raise RuntimeError("CHANNEL_ENCRYPTION_KEY inválido para producción") from e
                logger.warning("Usando clave de desarrollo (insegura)")

        if environment == "production":
            raise RuntimeError("CHANNEL_ENCRYPTION_KEY es obligatorio en producción")
        
        # Clave de desarrollo (no encriptada realmente)
        logger.warning("⚠ CHANNEL_ENCRYPTION_KEY no configurado. Usando clave dev (insegura)")
        return b"dev_unencrypted_key"

    def encrypt(self, plaintext: str) -> str:
        """
        Encripta un token/credencial.
        
        Args:
            plaintext: Token a encriptar (ej: "EAA...BCXYZ")
        
        Returns:
            Token encriptado (base64 URL-safe) o plaintext si no está configurado
        """
        if not self.encrypted or not self.cipher:
            # Dev mode: no encriptar
            return plaintext

        try:
            encrypted_bytes = self.cipher.encrypt(plaintext.encode())
            return encrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Error encriptando token: {e}")
            # Fallback: retornar plaintext
            return plaintext

    def decrypt(self, ciphertext: str) -> str:
        """
        Desencripta un token/credencial.
        
        Args:
            ciphertext: Token encriptado (resultado de encrypt())
        
        Returns:
            Token desencriptado (plaintext)
        """
        if not self.encrypted or not self.cipher:
            # Dev mode: no desencriptar
            return ciphertext

        try:
            decrypted_bytes = self.cipher.decrypt(ciphertext.encode())
            return decrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Error desencriptando token: {e}")
            # Si falla, asumir que es plaintext (migración gradual)
            return ciphertext

    def is_encrypted_mode(self) -> bool:
        """Retorna True si encryption está habilitado."""
        return self.encrypted


# Instancia global
_crypto_manager = TokenCryptoManager()


def encrypt_token(plaintext: str) -> str:
    """Encripta un token. Wrapper global."""
    return _crypto_manager.encrypt(plaintext)


def decrypt_token(ciphertext: str) -> str:
    """Desencripta un token. Wrapper global."""
    return _crypto_manager.decrypt(ciphertext)


def is_encryption_enabled() -> bool:
    """Retorna True si encryption está activo."""
    return _crypto_manager.is_encrypted_mode()


# CLI para generar/rotar claves
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "generate":
        new_key = Fernet.generate_key().decode()
        print("\n🔑 Nueva clave de encriptación generada:")
        print(f"\nCHANNEL_ENCRYPTION_KEY={new_key}\n")
        print("Agregá esto a tu .env y reinicia el servidor.")
        print("⚠  Guarda la clave en un lugar seguro (ej: 1Password, HashiCorp Vault)")
    else:
        print("\nUso: python crypto.py generate")
        print("     Genera una nueva clave de encriptación")
