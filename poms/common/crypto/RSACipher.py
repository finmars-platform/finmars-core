import base64

from Crypto.Cipher import PKCS1_OAEP
from Crypto.Cipher import PKCS1_v1_5
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA


## https://daniao.ws/rsa-java-to-python.html

class RSACipher():
    """
    RSA (assymmtetric) encryption
    """

    def encrypt(self, key, raw):
        """
        :param key: public key in "RSA/ECB/PKCS1Padding" 1024 RSA.
            keys are gnerated by:
                > openssl genrsa -out rsa_1024_priv.pem 1024
                > openssl rsa -pubout -in rsa_1024_priv.pem -out rsa_1024_pub.pem
        :param raw: raw data (usually AES key) to be incrypted as a type of bytes
        :return: base64 encoded bytes with encrypted "raw" text
        """
        public_key = RSA.importKey(base64.b64decode(key))
        ##cipher = PKCS1_OAEP.new(public_key, hashAlgo=SHA256)
        cipher = PKCS1_v1_5.new(public_key)
        return base64.b64encode(cipher.encrypt(bytes(raw, "utf-8")))

    def decrypt(self, key, enc):
        """
        :param key: private 1024 RSA key
        :param enc: base64 encoded tecrypted text as bytes (usually AES key)
        :return: recrypted  bytes
        """
        private_key = RSA.importKey(base64.b64decode(key))
        ##cipher = PKCS1_OAEP.new(private_key, hashAlgo=SHA256)
        cipher = PKCS1_v1_5.new(private_key)
        aes_incrypted_raw = base64.b64decode(enc)

        return cipher.decrypt(aes_incrypted_raw, "Error while decrypting")

    def createKey(self):
        """
        generates new RSA keys
        :return: Private Key, Public Key
        """
        key = RSA.generate(1024)
        privKey = key.exportKey("PEM")

        privKey = self.__trimKey(RSA.importKey(privKey))

        publKey = key.publickey().exportKey("PEM")
        publKey = self.__trimKey(RSA.importKey(publKey))
        return privKey, publKey

    def __trimKey(self, key: str):
        """
        :param key: private/public 1024 RSA key in PEM
        :return: key with removed first and last lines like "----BEGINING KEY---"
        """
        # newKey = b""
        # for line in key.splitlines():
        #     #if ( line.find("KEY----")<0 ) :
        #     if ( b"KEY----" in line ): continue
        #     newKey = newKey + line + b"\n"
        # return newKey

        key = key.replace("-----BEGIN PUBLIC KEY-----", "")
        key = key.replace("-----END PUBLIC KEY-----", "")
        return key
