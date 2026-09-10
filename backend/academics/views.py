from django.shortcuts import render

from google import genai
from google.genai import types
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAuthenticatedAnyRole
from django.conf import settings

from .models import Lecturer


# Created once when this module loads, not per-request — the client is
# just a lightweight wrapper around your API key, no expensive connection
# to keep open, so there's no benefit to recreating it on every request.
genai_client = genai.Client(api_key=settings.GEMINI_API_KEY)


class AssistantChatView(APIView):
    # Requires login (any role) — an AI endpoint with zero auth is an open
    # invitation for anyone on the internet to burn through your Gemini
    # API quota/billing for free, with nothing to stop them.
    permission_classes = [IsAuthenticatedAnyRole]

    def post(self, request):
        message = request.data.get('message', '').strip()
        if not message:
            return Response(
                {"error": "message is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # RAG step 1: pull REAL data from our own database first, scoped to
        # the logged-in user's own tenant. This is what stops a Faculty of
        # IT user from ever seeing another faculty's lecturer list, even
        # indirectly through the assistant's answer — the query itself
        # never fetches rows outside their tenant in the first place.
        lecturers = (
            Lecturer.objects
            .filter(tenant=request.user.tenant)
            .select_related('department')
        )

        if lecturers.exists():
            lecturer_lines = "\n".join(
                f"- {l.title} {l.name} ({l.department.name}"
                + (f", specializes in {l.specialization}" if l.specialization else "")
                + ")"
                for l in lecturers
            )
        else:
            # request.user.tenant can be None (e.g. your superuser, created
            # via createsuperuser, isn't tied to any faculty) — handle that
            # gracefully instead of crashing or sending Gemini an empty prompt.
            lecturer_lines = "(No lecturer data available for this account's tenant.)"

        # RAG step 2: hand Gemini the real data alongside the question, and
        # explicitly instruct it to only answer from that data. This is
        # what stops it from inventing plausible-sounding but completely
        # fake lecturer details it was never actually given.
        prompt = (
            f"Here is the current list of lecturers:\n{lecturer_lines}\n\n"
            f"Student question: {message}\n\n"
            "Answer using ONLY the lecturer information above. "
            "If the answer isn't in the data provided, say you don't have that information."
        )

        response = genai_client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                # Defines the assistant's persona/behavior — kept separate
                # from the actual data, which lives in the prompt above.
                system_instruction=(
                    "You are Lectra Academic Copilot, assisting university "
                    "students with course information, schedules, and "
                    "faculty inquiries. Be concise and factual."
                ),
            ),
        )

        return Response({"reply": response.text})
