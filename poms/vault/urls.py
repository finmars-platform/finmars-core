from rest_framework import routers

import poms.vault.views as vault

router = routers.DefaultRouter()
router.register(r'vault-status', vault.VaultStatusViewSet, 'vault-status')
router.register(r'vault-secret', vault.VaultSecretViewSet, 'vault-secret')
router.register(r'vault-engine', vault.VaultEngineViewSet, 'vault-engine')
