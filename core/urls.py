from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    # Item Master
    path("items/", views.ItemListView.as_view(), name="item-list"),
    path("items/create/", views.ItemCreateView.as_view(), name="item-create"),
    path("items/<int:pk>/edit/", views.ItemUpdateView.as_view(), name="item-update"),
    path("items/<int:pk>/toggle/", views.ItemToggleActiveView.as_view(), name="item-toggle"),
    path("items/bulk-toggle/", views.ItemBulkToggleView.as_view(), name="item-bulk-toggle"),
    path("items/export/", views.ItemExportView.as_view(), name="item-export"),
    path("items/import/", views.ItemImportView.as_view(), name="item-import"),
    # Lab Test Templates
    path("lab-templates/", views.LabTemplateListView.as_view(), name="lab-template-list"),
    path("lab-templates/create/", views.LabTemplateCreateView.as_view(), name="lab-template-create"),
    path("lab-templates/<int:pk>/edit/", views.LabTemplateUpdateView.as_view(), name="lab-template-update"),
    path("lab-templates/<int:pk>/delete/", views.LabTemplateDeleteView.as_view(), name="lab-template-delete"),
    # HTMX API
    path("api/item-search/", views.item_search_api, name="item-search-api"),
    path("api/item-price/", views.item_price_api, name="item-price-api"),
    path("api/item-search-json/", views.item_search_json, name="item-search-json"),
]
