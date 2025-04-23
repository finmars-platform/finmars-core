import base64
import logging

import Crypto
from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA
from Crypto.Util.number import ceil_div

_l = logging.getLogger("poms.common")


## https://daniao.ws/rsa-java-to-python.html


class RSACipher:
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

        modBits = Crypto.Util.number.size(private_key.n)
        k = ceil_div(modBits, 8)  # Convert from bits to bytes

        _l.debug("k %s" % k)
        _l.debug("len aes %s" % len(aes_incrypted_raw))

        return cipher.decrypt(aes_incrypted_raw, "Error while decrypting")

    def createKey(self):
        """
        generates new RSA keys
        :return: Private Key, Public Key
        """
        key = RSA.generate(1024)
        private_key = key.exportKey("PEM")
        private_key = self.__trimKey(private_key)

        public_key = key.publickey().exportKey("PEM")
        public_key = self.__trimKey(public_key)

        return private_key, public_key

    def __trimKey(self, key):
        """
        :param key: private/public 1024 RSA key in PEM
        :return: key with removed first and last lines like "----BEGINING KEY---"
        """

        decoded_key = key.decode("utf-8")

        newKey = ""
        for line in decoded_key.splitlines():
            # if ( line.find("KEY----")<0 ) :
            if "KEY----" in line:
                continue
            newKey = newKey + line + "\n"

        return newKey
