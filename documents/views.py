from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import DocumentRequest


@login_required
def documents_view(request):
    if request.user.is_admin_user:
        return redirect("documents:admin_requests")
    if not request.user.is_student:
        return redirect("core:home")

    my_requests = DocumentRequest.objects.filter(student=request.user)
    if request.method == "POST":
        doc_type = request.POST.get("doc_type")
        if doc_type and doc_type != "releve_notes":
            DocumentRequest.objects.create(student=request.user, doc_type=doc_type)
            messages.success(request, "Demande envoyée avec succès.")
        elif doc_type == "releve_notes":
            messages.warning(request, "Le relevé des notes n'est pas disponible pour le moment.")
        return redirect("documents:documents")
    return render(request, "documents/documents.html", {"my_requests": my_requests})


@login_required
def admin_requests(request):
    if not request.user.is_admin_user:
        return redirect("core:home")
    all_requests = DocumentRequest.objects.all().select_related("student")
    if request.method == "POST":
        req_id = request.POST.get("request_id")
        new_status = request.POST.get("status")
        doc_req = get_object_or_404(DocumentRequest, pk=req_id)
        doc_req.status = new_status
        doc_req.notes = request.POST.get("notes", "")
        doc_req.save()
        messages.success(request, "Statut mis à jour.")
        return redirect("documents:admin_requests")
    return render(request, "documents/admin_requests.html", {"all_requests": all_requests})
