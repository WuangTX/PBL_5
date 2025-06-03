from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('account.urls')),  # URLs gốc vẫn sử dụng account app
    path('account/', include('account.urls')),  # Thêm prefix account/ cho account app
    path('webadmin/', include('webadmin.urls')),
    path('webuser/', include('webuser.urls')),

]

# Thêm đường dẫn phục vụ file media trong chế độ phát triển
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)