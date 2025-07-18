from rest_framework import routers

import poms.vault.views as vault

router = routers.DefaultRouter()
router.register(r"vault", vault.VaultViewSet, "vault")
router.register(r"vault-secret", vault.VaultSecretViewSet, "vault-secret")
router.register(r"vault-engine", vault.VaultEngineViewSet, "vault-engine")
router.register(r"vault-record", vault.VaultRecordViewSet, "vault-record")
