from rest_framework import permissions

class IsAuthorOrReadOnly(permissions.BasePermission):
    """
    update/delete can only author
    read can all 
    """

    def has_object_permission(self, request, view, obj):
        # read all can
        if request.method in permissions.SAFE_METHODS: #GET, HEAD, OPTIONS
            return True
        
        return obj.author == request.user