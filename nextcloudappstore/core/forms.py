from django.conf import settings
from django.forms import (BooleanField, CharField, ChoiceField, Form,
                          RadioSelect, Textarea, TextInput)
from django.utils.translation import get_language_info
from django.utils.translation import ugettext_lazy as _  # type: ignore

from nextcloudappstore.core.models import App, AppRating

RATING_CHOICES = (
    (0.0, _('Bad')),
    (0.5, _('OK')),
    (1.0, _('Good'))
)

REGISTER_SIGN_CMD = ' echo -n "APP_ID" | openssl dgst -%s -sign ' \
                    '~/.nextcloud/certificates/APP_ID.key | openssl base64' % \
                    settings.CERTIFICATE_DIGEST
RELEASE_SIGN_CMD = (' openssl dgst -%s -sign '
                    '~/.nextcloud/certificates/APP_ID.key /path/to/app.tar.gz '
                    '| openssl base64' % settings.CERTIFICATE_DIGEST)
CREATE_CERT_CMD = ' openssl req -nodes -newkey rsa:4096 -keyout APP_ID.key ' \
                  '-out APP_ID.csr -subj "/CN=APP_ID"'


class AppReleaseUploadForm(Form):
    download = CharField(label=_('Download link (tar.gz)'), max_length=256,
                         widget=TextInput(attrs={'required': 'required'}))
    signature = CharField(widget=Textarea(attrs={'required': 'required'}),
                          label=_('Signature'),
                          help_text=_(
                              'Can be generated by executing the following '
                              'command:') + RELEASE_SIGN_CMD)
    nightly = BooleanField(label=_('Nightly'), required=False)


class AppRegisterForm(Form):
    certificate = CharField(
        widget=Textarea(attrs={'required': 'required'}),
        label=_('Public certificate'),
        help_text=_(
            'Usually stored in ~/.nextcloud/certificates/APP_ID.crt where '
            'APP_ID is your app\'s ID. If you do not have a certificate you '
            'need to create a certificate sign request (CSR) first, which '
            'should be posted on the <a '
            'href="https://github.com/nextcloud/app-certificate-requests" '
            'rel="noreferrer noopener">certificate repository</a> (follow '
            'the README). You can generate the CSR by executing the '
            'following command:') + CREATE_CERT_CMD)
    signature = CharField(widget=Textarea(attrs={'required': 'required'}),
                          label=_('Signature over your app\'s ID'),
                          help_text=_(
                              'Can be generated by executing the following '
                              'command:') + REGISTER_SIGN_CMD)
    safe_help_fields = ['certificate']


def get_languages_local(language=None):
    if language:
        languages = [language]
    else:
        languages = [lan[0] for lan in settings.LANGUAGES]

    return [(li['code'], li['name_local'])
            for li in [get_language_info(la) for la in languages]]


class AppRatingForm(Form):
    rating = ChoiceField(initial=0.5, choices=RATING_CHOICES,
                         widget=RadioSelect)
    language_code = ChoiceField(initial="", label=_('Language'),
                                choices=get_languages_local(),
                                help_text=_(
                                    '<b>Important</b>: Changing the language '
                                    'will clear your current comment. Changes '
                                    'will not be saved!')
                                )
    comment = CharField(widget=Textarea, required=False, label=_('Comment'))
    safe_help_fields = ['language_code']

    def __init__(self, *args, **kwargs):
        self._id = kwargs.pop('id', None)
        self._user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    class Meta:
        fields = ('rating', 'language_code', 'comment')

    def save(self):
        app = App.objects.get(id=self._id)
        app_rating, created = AppRating.objects.get_or_create(user=self._user,
                                                              app=app)
        app_rating.rating = self.cleaned_data['rating']
        app_rating.set_current_language(self.cleaned_data['language_code'])
        app_rating.comment = self.cleaned_data['comment']
        app_rating.save()
