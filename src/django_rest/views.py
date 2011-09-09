from django.views.decorators.csrf import csrf_exempt

class RestView(object):
    """
        A custom REST server to keep things simpler and more extensible than
        say, django-piston.
    """

    #
    # Ignore CSRF rules since APIs don't have to worry about such things.
    # Note that I tried to use the decorator, but it didn't seem to like
    # class-based views.
    #
    csrf_exempt = True

    def __call__(self, request, *a, **kwa):

        method = kwa["__method"]
        del(kwa["__method"])

        from django.core.exceptions import ValidationError, PermissionDenied
        from django.http import HttpResponseServerError, HttpResponseNotAllowed, HttpResponseBadRequest, Http404, HttpResponseNotFound

        try:
            params = self._authenticate_signature(request) # Returns parameters without the oauth_* stuff
            response = getattr(self, method)(request, *a, **kwa)
            response.content = response.content
            return response

        except Http404 as e:
            return HttpResponseNotFound(
                self._render("Not Found")
            )

        except ValidationError as e:
            return HttpResponseBadRequest(
                self._render(e.messages[0])
            )

        except PermissionDenied as e:
            if type(e.message) == tuple: # Bad Method
                return HttpResponseNotAllowed(
                    self._render(e.message)
                )
            else:
                return HttpResponseBadRequest(
                    self._render(e.message)
                )

        except Exception as e:

            # TODO: log this sort of thing
            print "\n\nUnhandled exception:\n  %s\n\n" % (e)
            return HttpResponseServerError(
                self._render("Server Error.  Please contact support")
            )


    def OK(self, content):
        from django.http import HttpResponse
        return HttpResponse(content=self._render(content), status=200, content_type="application/json")


    def CREATED(self, content):
        from django.http import HttpResponse
        return HttpResponse(content=self._render(content), status=201, content_type="application/json")


    def UPDATED(self):
        from django.http import HttpResponse
        return HttpResponse(content="", status=204)


    def DELETED(self):
        from django.http import HttpResponse
        return HttpResponse(content="", status=204)


    def _render(self, payload):
        """
            TODO: Switch on format
        """
        return self._output_json(payload)


    def _output_json(self, payload):

        from django.core.serializers.json import simplejson

        return simplejson.dumps(payload)


    def _authenticate_signature(self, request):
        """
            Basic OAuth authentication.  Thankfully, we don't have to
            implement the full 3-legged authentication process as this is a
            closed system.
        """

        from django.conf import settings

        if not hasattr(settings, "REST_USE_OAUTH") or not settings.REST_USE_OAUTH:
            return request.REQUEST

        import re,oauth2

        from django.core.exceptions import ValidationError
        from django.db.utils import IntegrityError

        from django_rest.models import Consumer, Nonce

        consumer = Consumer.objects.get(pk=1)

        server = oauth2.Server(signature_methods={'HMAC-SHA1': oauth2.SignatureMethod_HMAC_SHA1()})
        token  = oauth2.Token(key=consumer.access_key, secret=consumer.access_sec)

        req = None
        if request.method == "POST":
            req = oauth2.Request(method=request.method, url=request.build_absolute_uri(), parameters=request.POST)
        elif request.method == "GET":
            req = oauth2.Request(method=request.method, url=re.sub(r"\?.*", "", request.build_absolute_uri()), parameters=request.GET)

        # Nonce Checking
        n = request.REQUEST.get("oauth_nonce")
        if not n:
            raise ValidationError("OAuth failure: oauth_noce")

        nonce = Nonce(key=n)
        try:
            nonce.save() # This will fail on a key error if it's already in the database
        except IntegrityError:
            raise ValidationError("Nonce is no longer valid")

        # Signature Checking
        try:
            return server.verify_request(req, consumer, token) # Assuming the nonce passes, now we validate the key
        except Exception as e:
            raise ValidationError("OAuth failure: \n%s" % (e))
