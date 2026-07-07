
from .CDMSDataset import CDMSDataset
from .CDMSGroup import CDMSGroup
from .core import CatalogCore

class Dependents:
    def __init__(self, dc: CatalogCore) -> None:
        self.dc = dc

    @staticmethod
    def _resolve_container(dep_container, *, refresh_client = None):
        if isinstance(dep_container, CDMSDataset):
            try:
                container = dep_container.rawDataset
            except Exception:
                raise ValueError("Unqualified dataset passed as dependency container.")
            if refresh_client and getattr(container, "versionMetadata", None):
                if container.versionMetadata.get("dependencyName"):
                    container = refresh_client.path(
                            container.path, versionId=contaier.versionId, site="All"
                    )
            return container
        if isinstance(dep_container, CDMSGroup):
            try:
                container = dep_container.rawGroup
            except Exception:
                raise ValueError("Unqualified group passed as dependency container.")
            if refresh_client and getattr(container, "metadata", None):
                if container.metadata.get("dependencyName"):
                    container = refresh_client.path(container.path)
            return container
        return dep_container

    @staticmethod
    def _unwrap_groups(dep_groups):
        out = []
        for g in dep_groups or []:
            if isinstance(g, CDMSGroup):
                try:
                    out.append(g.rawGroup)
                except Exception:
                    raise ValueError("Unqualified group passed as dependent")
            else:
                out.append(g)
        return out

    @staticmethod
    def _unwrap_datasets(dep_datasets):
        out = []
        for d in dep_datasets or []:
            if isinstance(d, CDMSDataset):
                try:
                    out.append(d.rawDataset)
                except Exception:
                    raise ValueError("Unqualified dataset passed as dependent")
            else:
                out.append(d)
        return out

    @staticmethod
    def _write_back(dep_container, ret):
        if isinstance(dep_container, CDMSDataset):
            dep_container.rawDataset = ret
        elif isinstance(dep_container, CDMSGroup):
            dep_container.rawGroup = ret

    def get(self, dep_container, dep_type, max_depth, chunk_size, **kwargs):
        container = self._resolve_container(dep_container, refresh_client=self.dc.client)
        return self.dc.client.get_dependents(container, dep_type, max_depth, chunk_size, **kwargs)

    def get_next(self, dep_container, **kwargs):
        container = self._resolve_container(dep_container)
        return self.dc.client.get_next_dependents(container, **kwargs)

    def check_cycles(self, dep_container, dep_type, dep_dss=None, dep_grps=None):
        return self.dc.client.check_dependency_cycles(
                dep_container, dep_type, dep_dss, dep_grps)

    def add(self, dep_container, dep_type, dep_datasets=None, dep_groups=None, **kwargs):
        container = self._resolve_container(dep_container)
        ret = self.dc.client.add_dependents(
            container, dep_type,
            self._unwrap_datasets(dep_datasets),
            self._unwrap_groups(dep_groups),
            **kwargs,
        )
        self._write_back(dep_container, ret)

    def remove(self, dep_container, dep_type, dep_datasets=None, dep_groups=None, **kwargs):
        container = self._unwrap_container(dep_container)
        ret = self.dc.client.remove_dependents(
            container, dep_type,
            self._unwrap_datasets(dep_datasets),
            self._unwrap_groups(dep_groups),
            **kwargs,
        )
        self._write_back(dep_container, ret)


