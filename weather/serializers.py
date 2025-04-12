from rest_framework import serializers

class WeatherRequestSerializer(serializers.Serializer):
    city = serializers.CharField(max_length=100, required=False)
    country = serializers.CharField(max_length=100, required=False)
    latitude = serializers.FloatField(required=False)
    longitude = serializers.FloatField(required=False)

    def validate(self, data):
        if not (data.get('city') or data.get('country')) and not (data.get('latitude') and data.get('longitude')):
            raise serializers.ValidationError(
                "Either city and country or latitude and longitude must be provided."
            )
        return data