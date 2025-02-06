import logging
from customer.models import Customer
from cryptography.fernet import Fernet
from django.conf import settings as django_settings
from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
import rest_framework_simplejwt.exceptions as simplejwt_exceptions
from rest_framework_simplejwt.authentication import JWTTokenUserAuthentication

logger = logging.getLogger(__name__)


class CustomJWTAuthentication(JWTTokenUserAuthentication):
    """
    Custom JWT Authentication class to allow us to debug JWT Authentication Errors
    Base class
    https://github.com/SimpleJWT/django-rest-framework-simplejwt/blob/master/rest_framework_simplejwt/authentication.py
    """

    def authenticate(self, request):
        # 1) Get the JWT Token
        jwt_token = None
        jwt_in_header = self.get_jwt_from_header(request)
        jwt_in_queryparams = self.get_jwt_from_query_params(request)
        jwt_in_cookie = self.get_jwt_from_cookie(request)

        jwt_token = jwt_in_header or jwt_in_queryparams or jwt_in_cookie
        if jwt_token is None:
            logger.warning("Missing JWT Token")
            raise simplejwt_exceptions.AuthenticationFailed('Authentication credentials were not provided.')

        logger.debug(f"JWT Token has length {len(jwt_token or '')}")
        validated_token = self.get_validated_token(jwt_token)
        logger.debug("JWT Token decoded and validated.")

        self.set_validated_token_into_cookie(request, jwt_token)

        return self.get_user(validated_token), validated_token

    def set_validated_token_into_cookie(self, request, token):
        request.session[django_settings.SIMPLE_JWT['COOKIE_KEY']] = token
        logger.debug('Bearer token added to cookie.')

    def get_jwt_from_query_params(self, request):
        return request.query_params.get('jwt')

    def get_jwt_from_cookie(self, request):
        return request.session.get(django_settings.SIMPLE_JWT['COOKIE_KEY'])

    def get_jwt_from_header(self, request):
        """
        Extracts the header containing the JSON web token from the given
        request.
        Extracts an unvalidated JSON web token from the given "Authorization"
        header value.
        """
        header = request.META.get('HTTP_AUTHORIZATION')

        # if isinstance(header, str):
        #     # Work around django test client oddness
        #     header = header.encode(HTTP_HEADER_ENCODING)
        # rest_framework_simplejwt.authentication.AUTH_HEADER_TYPE_BYTES
        if header is None:
            return None

        parts = header.split()

        if len(parts) == 0:
            # Empty AUTHORIZATION header sent
            return None

        if parts[0] not in django_settings.SIMPLE_JWT['AUTH_HEADER_TYPES']:
            # Assume the header does not contain a JSON web token
            return None

        if len(parts) != 2:
            raise simplejwt_exceptions.AuthenticationFailed(
                'Authorization header must contain two space-delimited values',
                code='bad_authorization_header',
            )

        return parts[1]

    def get_user(self, validated_token):
        """
        Attempts to find and return a user using the given validated token.
        """
        try:
            user_id = validated_token['user_id']
        except KeyError:
            raise simplejwt_exceptions.InvalidToken('Token contained no recognizable user identification')
        user = Customer.objects.get(id=user_id)
        logger.debug(f'JWT Authentication returned User {user}. ')
        return user


class IsCustomer(BasePermission):
    """
    Allows access only to authenticated users.
    """

    def has_permission(self, request, view):
        return request.user and request.user.id


def encrypt_password(password):
    key = Fernet.generate_key()
    fernet = Fernet(key)
    return fernet.encrypt(password.encode()), key


def decrypt_password(password, key):
    fernet = Fernet(key)
    return fernet.decrypt(password).decode()


class LargeResultsSetPagination(PageNumberPagination):
    page_size = 32
    page_size_query_param = 'page_size'
    max_page_size = 10000