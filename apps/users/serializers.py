from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from apps.users.models import User
from apps.users.validators import validate_language, validate_timezone

class UserSerializer(serializers.ModelSerializer):
    """
    Docstring for UserSerializer
    """

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'date_joined', 'avatar']
        read_only_fields = ['id', 'date_joined']

class RegisterSerializer(serializers.ModelSerializer):
    """
    Docstring for RegisterSerializer for new user
    """
    password = serializers.CharField(write_only=True, min_length=6)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'password', 'password_confirm', 'language']

    def validate(self, attrs):
        """
        checking password
        """
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password': _("the passwords don't match")
            })
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm') # drop 
        user = User.objects.create_user(**validated_data)
        return user
    
class TimezoneSerializer(serializers.Serializer):
    """Serializer for change timezone"""
    timezone = serializers.CharField(validators=[validate_timezone])

class LanguageSerializer(serializers.Serializer):
    language = serializers.CharField(validators = [validate_language])