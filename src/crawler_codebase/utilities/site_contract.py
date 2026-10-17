"""
Adapter contract shared by the generic crawler pipeline and the concrete sites.

The pipeline is generic: it never branches on a site name. Instead every site
adapter declares which parts of the pipeline it is able to serve through a set
of capabilities, and the contract below defines what each capability requires
from the adapter. Adapters are allowed to be partial: a site that only knows
how to paginate and to fetch search pages is a legitimate adapter, it simply
cannot be selected for the stages it does not support.
"""

import functools

from abc import ABC, abstractmethod
from enum import Enum
from typing import Iterable, Optional

from bs4.element import Tag


# Key used to carry the product URL from search parsing to product fetching.
# It is the boundary between both stages, so it belongs to the contract.
PRODUCT_URL_KEY = "link"


class SiteCapability(Enum):
    """
    Units of pipeline functionality an adapter may or may not provide.
    """

    # Builds the paginated search URLs of a run (crawler seed).
    ALGORITHMIC_PAGINATION = "algorithmic_pagination"

    # Discovers the canonical pagination base on the live site (crawler seed).
    DYNAMIC_PAGINATION = "dynamic_pagination"

    # Knows when a search results page is ready (crawler search scraper).
    SEARCH_PAGE_READINESS = "search_page_readiness"

    # Extracts product URLs out of a search results page (crawler search parser).
    PRODUCT_URL_EXTRACTION = "product_url_extraction"

    # Knows when an individual product page is ready (crawler product scraper).
    PRODUCT_PAGE_READINESS = "product_page_readiness"

    # Parses an individual product page (crawler product parser).
    PRODUCT_PAGE_PARSING = "product_page_parsing"


# Pagination modes supported by the seed stage, and the capability each one
# additionally demands from the adapter.
PAGINATION_MODE_CAPABILITIES = {
    "algorithmic": SiteCapability.ALGORITHMIC_PAGINATION,
    "dynamic": SiteCapability.DYNAMIC_PAGINATION,
}


class SiteContractError(Exception):
    """Base error for every violation of the site adapter contract."""


class ConfigurationError(SiteContractError):
    """Raised when a run is configured in a way the contract cannot honour."""


class SiteCapabilityError(SiteContractError):
    """Raised when functionality is requested from an adapter that lacks it."""


def _implements(site_config: "WebsiteToScrape", method_name: str) -> bool:
    """
    True when the adapter overrides the given non-supported-by-default method.
    """
    implementation = getattr(type(site_config), method_name, None) #implementation = (class of the instance, method of that class, default None if no method found)
    return implementation is not getattr(WebsiteToScrape, method_name)


def _has_selector(site_config: "WebsiteToScrape", attribute_name: str) -> bool:
    """
    True when the adapter exposes a usable selector under the given name. 
    
    _has_selector() returns True when the adapter instance has an attribute with that name, the value is a string, and after trimming whitespace it is not empty.
    """
    selector = getattr(site_config, attribute_name, None)
    return isinstance(selector, str) and bool(selector.strip())


class WebsiteToScrape(ABC):
    """
    Contract every site adapter has to honour.

    Mandatory for all adapters:
        - ``SITE_NAME``
        - ``pagination_mode`` (a key of ``PAGINATION_MODE_CAPABILITIES``)
        - ``seed_urls``
        - ``product_extraction()``

    Everything else is capability gated: an adapter declares in
    ``CAPABILITIES`` what it supports, and the declaration is verified against
    the actual implementation when the adapter is instantiated.
    """

    SITE_NAME: str
    pagination_mode: str = "algorithmic"

    # Capabilities the concrete adapter claims to provide.
    CAPABILITIES: frozenset = frozenset()

    # Readiness selector of search results pages.
    # Required by SEARCH_PAGE_READINESS.
    selector_to_start_process: Optional[str] = None

    # Readiness selector of individual product pages.
    # Required by PRODUCT_PAGE_READINESS.
    wait_selector: Optional[str] = None

    def __init_subclass__(cls, **kwargs):
        """
        Makes the contract enforceable: adapters are validated on construction.
        """
        # This preserves the rest of the inheritance chain’s handling of the __init__subclass method. (POINT FOR FURTHER STUDY)
        super().__init_subclass__(**kwargs)

        # cls.__dict__ is a dictionary containing the attributes defined directly on that class. Here I am getting only the __init__ of the class.
        own_init = cls.__dict__.get("__init__")

        if own_init is None or getattr(own_init, "_validates_site_contract", False):
            return

        @functools.wraps(own_init)
        def __init__(self, *args, **kwargs):
            own_init(self, *args, **kwargs)

            # Only the outermost __init__ of the instantiated class validates,
            # so that adapters calling super().__init__() are checked once.
            # In other words, when nested wrapped __init__ methods run because of inheritance and super().__init__(), only the wrapper belonging to the actual class of the instance performs validation.
            # The idea is:
            # parent init logic may still run
            # but contract validation should happen once
            # for the actual adapter instance being created
            if type(self).__init__ is cls.__init__:
                self.validate_contract()

        __init__._validates_site_contract = True  # type: ignore[attr-defined]
        # Update the reference of the class' own init so it references the newly created init
        cls.__init__ = __init__  # type: ignore[assignment]

    # ---------------------------
    # Capabilities
    # ---------------------------
    # Frozen set is important to avoid modifications of a class' capabilities by any other part of the program.
    @classmethod
    def capabilities(cls) -> frozenset:
        """
        Capabilities declared by the adapter.
        """
        return frozenset(cls.CAPABILITIES)

    def supports(self, capability: SiteCapability) -> bool:
        """
        True when the adapter declares the given capability.
        """
        return capability in self.capabilities()

    def missing_capabilities(self, required: Iterable[SiteCapability]) -> frozenset:
        """
        Subset of the required capabilities the adapter does not provide.
        """
        return frozenset(required) - self.capabilities()

    def pagination_capability(self) -> SiteCapability:
        """
        Capability demanded by the pagination mode declared by the adapter.
        """
        try:
            return PAGINATION_MODE_CAPABILITIES[self.pagination_mode]
        except (KeyError, TypeError) as e:
            raise ConfigurationError(
                f"[{getattr(self, 'SITE_NAME', type(self).__name__)}] Unsupported pagination mode: "
                f"{self.pagination_mode!r}. Supported modes: "
                f"{sorted(PAGINATION_MODE_CAPABILITIES)}"
            ) from e

    def validate_contract(self) -> None:
        """
        Checks that what the adapter declares is what the adapter provides.
        """
        site_name = getattr(self, "SITE_NAME", type(self).__name__)

        if not getattr(self, "seed_urls", None):
            raise ConfigurationError(f"[{site_name}] Adapter defines no seed URLs.")

        for capability in self.capabilities():
            if not isinstance(capability, SiteCapability):
                raise SiteCapabilityError(
                    f"[{site_name}] Declared an unknown capability: {capability!r}"
                )

        # This section determines which pagination capability the declared pagination mode implies, then checks whether the adapter actually declared that capability; if not, it raises SiteCapabilityError.
        pagination_capability = self.pagination_capability()
        if not self.supports(pagination_capability):
            raise SiteCapabilityError(
                f"[{site_name}] Declares pagination mode {self.pagination_mode!r} "
                f"but not the required capability {pagination_capability.value}."
            )

        # The tuples of requirements mean: (1. capability being claimed, 2. method that should exist, 3. function used to verify it)
        requirements = (
            #for ALGORITHMIC_PAGINATION the implementation of build_pagination_url method is needed. does this adapter's class implement it, overriding the default implementation of websitetoscrape (parent class) or not? 
            (SiteCapability.ALGORITHMIC_PAGINATION, "build_pagination_url", _implements), 
            (SiteCapability.DYNAMIC_PAGINATION, "discover_first_paginated_url", _implements),
            (SiteCapability.PRODUCT_PAGE_PARSING, "individual_product_data_extraction", _implements),
            (SiteCapability.SEARCH_PAGE_READINESS, "selector_to_start_process", _has_selector),
            (SiteCapability.PRODUCT_PAGE_READINESS, "wait_selector", _has_selector),
        )

        # For each declared capability requirement, if the adapter claims to support that capability but fails the corresponding implementation check, raise SiteCapabilityError
        for capability, member, is_provided in requirements:
            if self.supports(capability) and not is_provided(self, member):
                raise SiteCapabilityError(
                    f"[{site_name}] Declares capability {capability.value} but does not "
                    f"provide {member!r}."
                )

    def require_capabilities(self, required: Iterable[SiteCapability]) -> None:
        """
        Raises a capability error unless the adapter provides everything required.
        """
        missing = self.missing_capabilities(required)

        if missing:
            site_name = getattr(self, "SITE_NAME", type(self).__name__)
            raise SiteCapabilityError(
                f"[{site_name}] Missing capabilities: "
                f"{', '.join(sorted(capability.value for capability in missing))}."
            )

    # ---------------------------
    # Pagination
    # ---------------------------

    #  base method
    # -> exists as part of the common interface
    # -> default behavior = "unsupported"

    # adapter declares capability
    # -> must override that method

    # adapter does not declare capability
    # -> inherited failing implementation is acceptable
    
    def build_pagination_url(self, base_url: str, page_number: int) -> str:
        """
        Returns the URL of the given search results page.
        Requires ALGORITHMIC_PAGINATION.
        """
        raise SiteCapabilityError(
            f"[{getattr(self, 'SITE_NAME', type(self).__name__)}] Does not support "
            f"{SiteCapability.ALGORITHMIC_PAGINATION.value}."
        )

    def discover_first_paginated_url(self, seed_url: str) -> str | None:
        """
        Returns the canonical pagination base discovered on the live site.
        Requires DYNAMIC_PAGINATION.
        """
        raise SiteCapabilityError(
            f"[{getattr(self, 'SITE_NAME', type(self).__name__)}] Does not support "
            f"{SiteCapability.DYNAMIC_PAGINATION.value}."
        )

    # ---------------------------
    # Parsing
    # ---------------------------
    @abstractmethod
    def product_extraction(self, soup: Tag) -> list[dict] | None:
        """
        Returns the products found in a search results page.

        Adapters declaring PRODUCT_URL_EXTRACTION must include the product URL
        of every returned product under the PRODUCT_URL_KEY key, which is what
        the product scraper consumes afterwards.
        """
        pass

    def individual_product_data_extraction(self, soup: Tag) -> dict:
        """
        Returns the product data found in an individual product page.
        Requires PRODUCT_PAGE_PARSING.
        """
        raise SiteCapabilityError(
            f"[{getattr(self, 'SITE_NAME', type(self).__name__)}] Does not support "
            f"{SiteCapability.PRODUCT_PAGE_PARSING.value}."
        )