import csv
import io

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.views import View
from django.views.decorators.http import require_GET

from .models import Item
from .forms import ItemForm


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Only admins can manage the item master."""
    def test_func(self):
        return self.request.user.role == "ADMIN"


class ItemListView(AdminRequiredMixin, View):
    def get(self, request):
        query = request.GET.get("q", "").strip()
        category = request.GET.get("category", "")
        department = request.GET.get("department", "")
        status = request.GET.get("status", "")

        items = Item.objects.all()

        if query:
            items = items.filter(
                Q(name__icontains=query) |
                Q(item_code__icontains=query) |
                Q(description__icontains=query)
            )
        if category:
            items = items.filter(category=category)
        if department:
            items = items.filter(department=department)
        if status == "active":
            items = items.filter(is_active=True)
        elif status == "inactive":
            items = items.filter(is_active=False)

        items = items.order_by("category", "name")

        context = {
            "items": items,
            "query": query,
            "selected_category": category,
            "selected_department": department,
            "selected_status": status,
            "categories": Item.Category.choices,
            "departments": Item.Department.choices,
            "total_count": items.count(),
        }
        return render(request, "core/item_list.html", context)


class ItemCreateView(AdminRequiredMixin, View):
    def get(self, request):
        form = ItemForm()
        return render(request, "core/item_form.html", {"form": form, "title": "Add New Item"})

    def post(self, request):
        form = ItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.created_by = request.user
            item.save()
            messages.success(request, f"Item '{item.name}' created successfully.")
            return redirect("core:item-list")
        return render(request, "core/item_form.html", {"form": form, "title": "Add New Item"})


class ItemUpdateView(AdminRequiredMixin, View):
    def get(self, request, pk):
        item = get_object_or_404(Item, pk=pk)
        form = ItemForm(instance=item)
        return render(request, "core/item_form.html", {"form": form, "item": item, "title": f"Edit Item - {item.name}"})

    def post(self, request, pk):
        item = get_object_or_404(Item, pk=pk)
        form = ItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, f"Item '{item.name}' updated successfully.")
            return redirect("core:item-list")
        return render(request, "core/item_form.html", {"form": form, "item": item, "title": f"Edit Item - {item.name}"})


class ItemToggleActiveView(AdminRequiredMixin, View):
    def post(self, request, pk):
        item = get_object_or_404(Item, pk=pk)
        item.is_active = not item.is_active
        item.save(update_fields=["is_active", "updated_at"])
        status = "activated" if item.is_active else "deactivated"
        messages.success(request, f"Item '{item.name}' has been {status}.")
        return redirect("core:item-list")


class ItemBulkToggleView(AdminRequiredMixin, View):
    def post(self, request):
        action = request.POST.get("action")
        item_ids = request.POST.getlist("item_ids")
        if not item_ids:
            messages.warning(request, "No items selected.")
            return redirect("core:item-list")
        items = Item.objects.filter(pk__in=item_ids)
        if action == "activate":
            count = items.update(is_active=True)
            messages.success(request, f"{count} item(s) activated.")
        elif action == "deactivate":
            count = items.update(is_active=False)
            messages.success(request, f"{count} item(s) deactivated.")
        return redirect("core:item-list")


class ItemExportView(AdminRequiredMixin, View):
    def get(self, request):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="item_master_export.csv"'

        writer = csv.writer(response)
        writer.writerow([
            "Item Code", "Name", "Category", "Description",
            "Unit Price (KSH)", "Cost Price (KSH)", "Unit of Measure",
            "Normal Range", "Unit", "Department", "Active",
        ])

        items = Item.objects.all().order_by("category", "name")
        for item in items:
            writer.writerow([
                item.item_code, item.name, item.get_category_display(),
                item.description, item.unit_price, item.cost_price,
                item.unit_of_measure, item.normal_range, item.unit,
                item.get_department_display(),
                "Yes" if item.is_active else "No",
            ])

        return response


class ItemImportView(AdminRequiredMixin, View):
    def get(self, request):
        return render(request, "core/item_import.html")

    def post(self, request):
        csv_file = request.FILES.get("csv_file")
        if not csv_file:
            messages.error(request, "Please upload a CSV file.")
            return redirect("core:item-import")

        if not csv_file.name.endswith(".csv"):
            messages.error(request, "File must be a .csv file.")
            return redirect("core:item-import")

        try:
            decoded = csv_file.read().decode("utf-8")
            reader = csv.DictReader(io.StringIO(decoded))

            created = 0
            skipped = 0
            errors = []

            for i, row in enumerate(reader, start=2):
                name = row.get("Name", "").strip()
                if not name:
                    skipped += 1
                    continue

                category = row.get("Category", "OTHER").strip()
                valid_categories = [c[0] for c in Item.Category.choices]
                if category not in valid_categories:
                    errors.append(f"Row {i}: Invalid category '{category}'")
                    skipped += 1
                    continue

                try:
                    price = float(row.get("Unit Price", 0))
                except (ValueError, TypeError):
                    price = 0

                try:
                    cost = float(row.get("Cost Price", 0))
                except (ValueError, TypeError):
                    cost = 0

                department = row.get("Department", "OTHER").strip()
                valid_depts = [d[0] for d in Item.Department.choices]
                if department not in valid_depts:
                    department = "OTHER"

                unit = row.get("Unit of Measure", "Unit").strip()
                normal_range = row.get("Normal Range", "").strip()
                test_unit = row.get("Unit", "").strip()

                Item.objects.create(
                    name=name,
                    category=category,
                    description=row.get("Description", "").strip(),
                    unit_price=price,
                    cost_price=cost,
                    unit_of_measure=unit,
                    normal_range=normal_range,
                    unit=test_unit,
                    department=department,
                    created_by=request.user,
                )
                created += 1

            if errors:
                messages.warning(request, f"Imported {created} item(s). {len(errors)} error(s): {'; '.join(errors[:5])}")
            else:
                messages.success(request, f"Successfully imported {created} item(s). {skipped} skipped.")

        except Exception as e:
            messages.error(request, f"Import failed: {str(e)}")

        return redirect("core:item-list")


# ── HTMX Searchable Dropdown API ─────────────────────────────────────

@require_GET
def item_search_api(request):
    """HTMX-powered search endpoint for items. Returns HTML fragments for
    use in searchable dropdowns across all modules."""
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")

    items = Item.objects.filter(is_active=True)
    if query:
        items = items.filter(
            Q(name__icontains=query) |
            Q(item_code__icontains=query)
        )
    if category:
        items = items.filter(category=category)

    items = items.order_by("name")[:50]

    return render(request, "core/_item_search_results.html", {"items": items})


@require_GET
def item_price_api(request):
    """Return item price as JSON for auto-fill on selection."""
    item_id = request.GET.get("item_id")
    if not item_id:
        return JsonResponse({"error": "No item_id provided"}, status=400)
    try:
        item = Item.objects.get(pk=item_id, is_active=True)
        return JsonResponse({
            "id": item.pk,
            "item_code": item.item_code,
            "name": item.name,
            "unit_price": str(item.unit_price),
            "unit_of_measure": item.unit_of_measure,
            "category": item.category,
        })
    except Item.DoesNotExist:
        return JsonResponse({"error": "Item not found"}, status=404)


@require_GET
def item_search_json(request):
    """JSON search endpoint for Item Master. Used by consultation page
    searchable dropdowns for lab tests, radiology, ultrasound, etc."""
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")

    items = Item.objects.filter(is_active=True)
    if query:
        items = items.filter(
            Q(name__icontains=query) |
            Q(item_code__icontains=query)
        )
    if category:
        # Support comma-separated categories
        cats = [c.strip() for c in category.split(",") if c.strip()]
        items = items.filter(category__in=cats)

    items = items.order_by("name")[:30]

    data = [
        {
            "id": item.pk,
            "item_code": item.item_code,
            "name": item.name,
            "unit_price": str(item.unit_price),
            "unit_of_measure": item.unit_of_measure,
            "category": item.category,
            "category_display": item.get_category_display(),
            "normal_range": item.normal_range,
            "unit": item.unit,
        }
        for item in items
    ]
    return JsonResponse({"results": data})


# ── Lab Test Template Management (Admin) ────────────────────────────

class LabTemplateListView(AdminRequiredMixin, View):
    def get(self, request):
        from laboratory.models import LabTestTemplate
        templates = (
            LabTestTemplate.objects
            .select_related("lab_test")
            .prefetch_related("parameters")
            .order_by("lab_test__category", "lab_test__name")
        )
        return render(request, "core/lab_template_list.html", {
            "templates": templates,
            "total_count": templates.count(),
        })


class LabTemplateCreateView(AdminRequiredMixin, View):
    def get(self, request):
        from laboratory.models import LabTest, LabTestTemplate
        lab_tests = LabTest.objects.filter(is_active=True).order_by("category", "name")
        existing_ids = LabTestTemplate.objects.values_list("lab_test_id", flat=True)
        return render(request, "core/lab_template_form.html", {
            "lab_tests": lab_tests,
            "existing_ids": list(existing_ids),
            "title": "Create Lab Test Template",
        })

    def post(self, request):
        from laboratory.models import LabTest, LabTestTemplate, LabTestParameter
        lab_test_id = request.POST.get("lab_test")
        instructions = request.POST.get("instructions", "").strip()

        try:
            lab_test = LabTest.objects.get(pk=lab_test_id)
        except (LabTest.DoesNotExist, ValueError):
            messages.error(request, "Invalid lab test selected.")
            return redirect("core:lab-template-list")

        if LabTestTemplate.objects.filter(lab_test=lab_test).exists():
            messages.warning(request, f"A template already exists for {lab_test.name}.")
            return redirect("core:lab-template-list")

        template = LabTestTemplate.objects.create(
            lab_test=lab_test,
            instructions=instructions,
            created_by=request.user,
        )

        names = request.POST.getlist("param_name[]")
        units = request.POST.getlist("param_unit[]")
        ranges = request.POST.getlist("param_range[]")
        mins = request.POST.getlist("param_min[]")
        maxs = request.POST.getlist("param_max[]")

        for i, name in enumerate(names):
            name = name.strip()
            if not name:
                continue
            normal_min = None
            normal_max = None
            try:
                normal_min = float(mins[i]) if mins[i].strip() else None
            except (ValueError, IndexError):
                pass
            try:
                normal_max = float(maxs[i]) if maxs[i].strip() else None
            except (ValueError, IndexError):
                pass

            LabTestParameter.objects.create(
                template=template,
                name=name,
                unit=units[i].strip() if i < len(units) else "",
                normal_range=ranges[i].strip() if i < len(ranges) else "",
                normal_min=normal_min,
                normal_max=normal_max,
                display_order=i,
            )

        messages.success(request, f"Template created for {lab_test.name} with {template.parameters.count()} parameters.")
        return redirect("core:lab-template-list")


class LabTemplateUpdateView(AdminRequiredMixin, View):
    def get(self, request, pk):
        from laboratory.models import LabTestTemplate
        template = get_object_or_404(LabTestTemplate.objects.select_related("lab_test"), pk=pk)
        parameters = template.parameters.order_by("display_order", "name")
        return render(request, "core/lab_template_form.html", {
            "template": template,
            "parameters": parameters,
            "title": f"Edit Template - {template.lab_test.name}",
            "editing": True,
        })

    def post(self, request, pk):
        from laboratory.models import LabTestTemplate, LabTestParameter
        template = get_object_or_404(LabTestTemplate, pk=pk)
        template.instructions = request.POST.get("instructions", "").strip()
        template.save(update_fields=["instructions", "updated_at"])

        template.parameters.all().delete()

        names = request.POST.getlist("param_name[]")
        units = request.POST.getlist("param_unit[]")
        ranges = request.POST.getlist("param_range[]")
        mins = request.POST.getlist("param_min[]")
        maxs = request.POST.getlist("param_max[]")

        count = 0
        for i, name in enumerate(names):
            name = name.strip()
            if not name:
                continue
            normal_min = None
            normal_max = None
            try:
                normal_min = float(mins[i]) if mins[i].strip() else None
            except (ValueError, IndexError):
                pass
            try:
                normal_max = float(maxs[i]) if maxs[i].strip() else None
            except (ValueError, IndexError):
                pass

            LabTestParameter.objects.create(
                template=template,
                name=name,
                unit=units[i].strip() if i < len(units) else "",
                normal_range=ranges[i].strip() if i < len(ranges) else "",
                normal_min=normal_min,
                normal_max=normal_max,
                display_order=i,
            )
            count += 1

        messages.success(request, f"Template updated: {count} parameters saved.")
        return redirect("core:lab-template-list")


class LabTemplateDeleteView(AdminRequiredMixin, View):
    def post(self, request, pk):
        from laboratory.models import LabTestTemplate
        template = get_object_or_404(LabTestTemplate, pk=pk)
        name = template.lab_test.name
        template.delete()
        messages.success(request, f"Template for '{name}' deleted.")
        return redirect("core:lab-template-list")
