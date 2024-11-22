from django.urls import path
from . import views 

urlpatterns = [

    #path('characters/', views.character_list, name='character_list'),
    #path('', views.post_list, name='post_list'),  
    path('', views.post_list, name='character_list'),
    path('character/<str:id_character>/', views.character_detail, name='character_detail'),
    path('character/<str:id_character>/?<str:message>', views.character_detail, name='character_detail_mes'),
    path('character/<str:character_name>/', views.character_detail, name='character_detail'),
    path('update_equipment/<int:character_id>/', views.update_equipment, name='update_equipment'),

]