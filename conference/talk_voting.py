from django.conf.urls import url
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Prefetch
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse

from conference.models import Conference, Talk, VotoTalk


@login_required
def talk_voting(request):

    current_conference = Conference.objects.current()

    if not current_conference.voting():
        return TemplateResponse(
            request, "ep19/bs/talk_voting/voting_is_closed.html"
        )

    if not is_user_allowed_to_vote(request.user):
        return TemplateResponse(
            request, "ep19/bs/talk_voting/voting_is_unavailable.html", {
                'conference': current_conference,
            }
        )

    talks = (
        Talk.objects.filter(
            Q(conference=current_conference.code) & ~Q(created_by=request.user)
        )
        .order_by("?")
        .prefetch_related(
            Prefetch(
                "vototalk_set",
                queryset=VotoTalk.objects.filter(user=request.user),
                to_attr="votes",
            )
        )
    )

    return TemplateResponse(
        request,
        "ep19/bs/talk_voting/voting.html",
        {"talks": talks, "VotingOptions": VotingOptions},
    )


def is_user_allowed_to_vote(user):
    """
    Checks if user is allowed to vote at the moment of accessing this function
    This usually means checking if they have at least one ticket associated
    with their account (either for this or any of the past years
    """
    return user.ticket_set.all().exists()


@login_required
def vote_on_a_talk(request, talk_uuid):
    talk = get_object_or_404(Talk, uuid=talk_uuid)

    try:
        db_vote = VotoTalk.objects.get(user=request.user, talk=talk)
    except VotoTalk.DoesNotExist:
        db_vote = None

    if request.method == "POST":
        vote = int(request.POST.get("vote"))
        assert vote in VotingOptions.ALL

        try:
            db_vote = VotoTalk.objects.get(user=request.user, talk=talk)

        except VotoTalk.DoesNotExist:

            if vote == VotingOptions.no_vote:
                return TemplateResponse(
                    request,
                    "ep19/bs/talk_voting/_voting_form.html",
                    {
                        "talk": talk,
                        "db_vote": None,
                        "VotingOptions": VotingOptions,
                    },
                )

            db_vote = VotoTalk.objects.create(
                user=request.user, talk=talk, vote=vote
            )

        if vote == VotingOptions.no_vote:
            db_vote.delete()
            return TemplateResponse(
                request,
                "ep19/bs/talk_voting/_voting_form.html",
                {
                    "talk": talk,
                    "db_vote": None,
                    "VotingOptions": VotingOptions,
                },
            )

        db_vote.vote = vote
        db_vote.save()

    return TemplateResponse(
        request,
        "ep19/bs/talk_voting/_voting_form.html",
        {"talk": talk, "db_vote": db_vote, "VotingOptions": VotingOptions},
    )


class VotingOptions:
    no_vote = -1
    not_interested = 0
    maybe = 3
    want_to_see = 7
    must_see = 10

    ALL = [no_vote, not_interested, maybe, want_to_see, must_see]


urlpatterns = [
    url(r"^$", talk_voting, name="talks"),
    url(r"^vote-on/(?P<talk_uuid>[\w]+)/$", vote_on_a_talk, name="vote"),
]