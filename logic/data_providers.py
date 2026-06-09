import openapi_client as openapi_client
from openapi_client import MemberDTO
from openapi_client.api.members_api import MembersApi
from openapi_client.api.member_transactions_api import MemberTransactionsApi
from openapi_client.exceptions import ApiException
from typing import Callable


class DataSourceMeta(type):

    def __instancecheck__(self, instance):
        return self.__subclasscheck__(type(instance))

    def __subclasscheck__(self, subclass):
        return (hasattr(subclass, 'get_record') and
                callable(subclass.get_record) and
                hasattr(subclass, 'get_records_count') and
                callable(subclass.get_records_count) and
                hasattr(subclass, 'get_records') and
                callable(subclass.get_records))


class DataSourceInterface(metaclass=DataSourceMeta):
    pass


class BaseDataSource(DataSourceInterface):
    _cache = None

    def __new__(cls, **kwargs):
        cls._cache = []
        return cls

    @classmethod
    def get_records(cls) -> list:
        pass

    @classmethod
    def get_record(cls, index: int) -> object:
        if len(cls._cache) == 0:
            raise ValueError('empty data source')
        if index > len(cls._cache):
            raise ValueError('index is greater then records count')
        return cls._cache[index]

    @classmethod
    def get_records_count(cls) -> int:
        if len(cls._cache) == 0:
            cls._cache = cls.get_records()
        return len(cls._cache)


class OpenApiDataSource(BaseDataSource):

    def __new__(cls, host: str, access_token: str, *args, **kwargs):
        cls._host = host
        cls._token = access_token
        return super().__new__(cls)

    @classmethod
    def init_api_client(cls) -> openapi_client.ApiClient:
        re_swynca_config = openapi_client.Configuration(host=cls._host)
        api_client = openapi_client.ApiClient(configuration=re_swynca_config)
        api_client.set_default_header("Authorization", "Bearer " + cls._token)
        return api_client


class TransactionDataSource(OpenApiDataSource):

    def __new__(cls, host: str, access_token: str, user_id: int):
        cls._user_id = user_id
        return super().__new__(cls, host, access_token)

    @classmethod
    def get_records(cls) -> list:
        with cls.init_api_client() as api_client:
            api_instance = openapi_client.TransactionsApi(api_client)
            try:
                api_response = api_instance.transaction_log(cls._user_id)
                return api_response
            except ApiException as e:
                print("Exception when calling ResidentsApi->list_residents: %s\n" % e)
        return []


class ResidentDataSource(OpenApiDataSource):

    @classmethod
    def get_records(cls) -> list:
        with cls.init_api_client() as api_client:
            api_instance = openapi_client.ResidentsApi(api_client)
            limit = 100
            offset = 0
            try:
                api_response = api_instance.list_residents(limit=limit, offset=offset)
                return api_response
            except ApiException as e:
                print("Exception when calling ResidentsApi->list_residents: %s\n" % e)
        return []


class BalanceFromReSwynca(OpenApiDataSource):
    _user_id: str

    def __new__(cls, host: str, access_token: str, user_id: str, *args, **kwargs):
        cls._user_id = user_id
        return super().__new__(cls, host, access_token)

    @classmethod
    def get_records(cls) -> list:
        result = []
        with super().init_api_client() as api_client:
            members_api = MembersApi(api_client)
            members = members_api.members_controller_find_all()
            if len(members) == 0:
                return result
            for m in members:
                if m.telegram_metadata is not None and m.telegram_metadata.telegram_id == cls._user_id:
                    return [{cls._user_id: m.balance}]
            return result


class TransactionsFromReSwynca(OpenApiDataSource):
    _user_id: str

    def __new__(cls, host: str, access_token: str, user_id: str, *args, **kwargs):
        cls._user_id = user_id
        return super().__new__(cls, host, access_token)

    @classmethod
    def get_records(cls) -> list:
        result = []
        with super().init_api_client() as api_client:
            members_api = MembersApi(api_client)
            tran_api = MemberTransactionsApi(api_client)
            members = members_api.members_controller_find_all()
            if len(members) == 0:
                return result
            for m in members:
                if m.telegram_metadata is not None and m.telegram_metadata.telegram_id == cls._user_id:
                    limit = 50
                    offset = 0
                    while True:
                        trans = tran_api.member_transactions_controller_find_all_by_subject_member(
                            member_id=m.id,
                            offset=str(offset),
                            count=str(limit),
                            order_by='created_at',
                            order_direction='asc'
                        )
                        result.extend(trans.transactions)
                        if len(result) >= trans.count:
                            return result
                        offset += limit
            return result


class ActiveMembersFromReSwyncaDataSource(OpenApiDataSource):
    _user_id: str

    def __new__(cls, host: str, access_token: str, user_id: str, *args, **kwargs):
        cls._user_id = user_id
        return super().__new__(cls, host, access_token)

    @classmethod
    def get_records(cls) -> list:
        with super().init_api_client() as api_client:
            members_api = MembersApi(api_client)
            resp = members_api.members_controller_find_all()
            only_active: Callable[[MemberDTO], bool] = \
                lambda r: isinstance(r, MemberDTO) \
                          and r.status == 'active' \
                          and r.telegram_metadata is not None \
                          and r.telegram_metadata.telegram_name is not None
            return list(filter(only_active, resp))
