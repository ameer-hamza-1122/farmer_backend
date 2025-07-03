import requests
from django.conf import settings
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import WeatherRequestSerializer
from authentication import CustomJWTAuthentication, IsCustomer

class WeatherView(APIView):
    authentication_classes = (CustomJWTAuthentication,)
    permission_classes = (IsCustomer,)
    def post(self, request):
        serializer = WeatherRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        api_key = settings.OPENWEATHERMAP_API_KEY
        base_url = "http://api.openweathermap.org/data/2.5/weather"

        # Prepare query parameters
        if data.get('city') or data.get('country'):
            if data.get('city') and not data.get('country'):
                query = data['city']
            elif data.get('country') and not data.get('city'):
                query = data['country']
            else:
                query = f"{data['city']},{data['country']}"
            params = {"q": query, "appid": api_key, "units": "metric"}
        else:
            params = {
                "lat": data['latitude'],
                "lon": data['longitude'],
                "appid": api_key,
                "units": "metric",
            }

        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()
            weather_data = response.json()
            return Response(weather_data, status=status.HTTP_200_OK)

        except requests.exceptions.RequestException as e:
            return Response({"error": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)