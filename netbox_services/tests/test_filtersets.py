# SPDX-License-Identifier: AGPL-3.0-or-later
"""FilterSet tests against a real DB (no mocks): the explicit FK + choice filters and search."""
from django.test import TestCase
from ..choices import HAStrategyChoices, ProviderScopeChoices, ServiceInstanceStatusChoices
from ..filtersets import (
    IntegrationCatalogFilterSet, IntegrationFilterSet, ServiceCatalogFilterSet, ServiceInstanceFilterSet,
)
from ..models import Integration, IntegrationCatalog, ServiceCatalog, ServiceInstance
from .utils import make_catalog, make_instance


class ServiceCatalogFilterTest(TestCase):
    queryset = ServiceCatalog.objects.all()
    filterset = ServiceCatalogFilterSet

    @classmethod
    def setUpTestData(cls):
        make_catalog("forgejo", tier=1, requires_gpu=False)
        make_catalog("vllm", tier=2, requires_gpu=True, ha_strategy=HAStrategyChoices.NONE)
        make_catalog("wordpress", tier=1, ha_strategy=HAStrategyChoices.CONTENT_RSYNC)

    def test_name(self):
        self.assertEqual(self.filterset({"name": ["forgejo"]}, self.queryset).qs.count(), 1)

    def test_requires_gpu(self):
        self.assertEqual(self.filterset({"requires_gpu": True}, self.queryset).qs.count(), 1)

    def test_ha_strategy(self):
        self.assertEqual(
            self.filterset({"ha_strategy": [HAStrategyChoices.CONTENT_RSYNC]}, self.queryset).qs.count(), 1
        )

    def test_search(self):
        self.assertEqual(self.filterset({"q": "word"}, self.queryset).qs.count(), 1)


class IntegrationCatalogFilterTest(TestCase):
    queryset = IntegrationCatalog.objects.all()
    filterset = IntegrationCatalogFilterSet

    @classmethod
    def setUpTestData(cls):
        cat = make_catalog("authentik")
        IntegrationCatalog.objects.create(catalog=cat, type="openbao", requires_service="openbao",
                                          provider_scope=ProviderScopeChoices.DEDICATED)
        IntegrationCatalog.objects.create(catalog=cat, type="alloy", requires_service="alloy")

    def test_catalog_by_name(self):
        self.assertEqual(self.filterset({"catalog": ["authentik"]}, self.queryset).qs.count(), 2)

    def test_provider_scope(self):
        self.assertEqual(
            self.filterset({"provider_scope": [ProviderScopeChoices.DEDICATED]}, self.queryset).qs.count(), 1
        )

    def test_requires_service(self):
        self.assertEqual(self.filterset({"requires_service": ["openbao"]}, self.queryset).qs.count(), 1)


class ServiceInstanceFilterTest(TestCase):
    queryset = ServiceInstance.objects.all()
    filterset = ServiceInstanceFilterSet

    @classmethod
    def setUpTestData(cls):
        cls.cat = make_catalog("forgejo")
        make_instance(cls.cat, hostname="fj-1", status=ServiceInstanceStatusChoices.ACTIVE)
        make_instance(cls.cat, hostname="fj-2", status=ServiceInstanceStatusChoices.STAGED)

    def test_catalog_id(self):
        self.assertEqual(self.filterset({"catalog_id": [self.cat.pk]}, self.queryset).qs.count(), 2)

    def test_status(self):
        self.assertEqual(
            self.filterset({"status": [ServiceInstanceStatusChoices.ACTIVE]}, self.queryset).qs.count(), 1
        )

    def test_search_hostname(self):
        self.assertEqual(self.filterset({"q": "fj-1"}, self.queryset).qs.count(), 1)


class IntegrationFilterTest(TestCase):
    queryset = Integration.objects.all()
    filterset = IntegrationFilterSet

    @classmethod
    def setUpTestData(cls):
        openbao = make_catalog("openbao")
        authentik = make_catalog("authentik")
        IntegrationCatalog.objects.create(catalog=authentik, type="openbao", requires_service="openbao")
        cls.consumer = make_instance(authentik, hostname="authentik")
        provider = make_instance(openbao, hostname="openbao")
        Integration.objects.create(consumer=cls.consumer, provider=provider, type="openbao")

    def test_consumer_id(self):
        self.assertEqual(self.filterset({"consumer_id": [self.consumer.pk]}, self.queryset).qs.count(), 1)

    def test_type(self):
        self.assertEqual(self.filterset({"type": ["openbao"]}, self.queryset).qs.count(), 1)
