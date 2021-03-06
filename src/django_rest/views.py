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

	request = None

	def __call__(self, request, *a, **kwa):

		from django.conf import settings

		method = kwa["__method"]
		del(kwa["__method"])

		self.request = request
		self._setup_data()

		# Check for the sexy header
		if "HTTP_X_SEXY" in self.request.META:
			self.sexy = True

		from django.core.exceptions import ValidationError, PermissionDenied
		from django.http import HttpResponseServerError, HttpResponseNotAllowed, HttpResponseBadRequest, Http404, HttpResponseNotFound, HttpResponse

		try:

			params = self._authenticate_signature() # Returns parameters without the oauth_* stuff

			if settings.REST_USE_CORS and request.method == "OPTIONS":

				response = HttpResponse()

			else:

				print (request.method, type(self), getattr(self, method), a, kwa, request.DATA)
				response = getattr(self, method)(*a, **kwa)
				response.content = response.content

			if settings.REST_USE_CORS:
				response["Access-Control-Allow-Origin"] = "*"
				response["Access-Control-Allow-Credentials"] = "true"
				response["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE"
				response["Access-Control-Max-Age"] = "1728000"
				response["Access-Control-Allow-Headers"] = "authorization"

			return response

		except Http404:
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

			import sys,traceback

			# TODO: log this sort of thing
			print "\n\nUnhandled exception:\n  %s\n\n" % e
			traceback.print_exc(file=sys.stdout)

			if settings.DEBUG:
				return HttpResponseServerError(self._render(u"Server error: %s" % e))
			else:
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
		return HttpResponse(status=204)


	def DELETED(self):
		from django.http import HttpResponse
		return HttpResponse(status=204)


	def _setup_data(self):

		self.request.DATA = []

		if self.request.method == "GET":
			self.request.DATA = self.request.GET
		elif self.request.method == "POST":
			self.request.DATA = self.request.POST
		elif self.request.method in ("PUT","DELETE",):
			from urlparse import parse_qs
			data = dict(parse_qs(self.request.raw_post_data).items())
			for k,v in data.items():
				if len(v) == 1:
					data[k] = v.pop()
			self.request.DATA = data


	def _render(self, payload):
		"""
			TODO: Switch on format
		"""
		return self._output_json(payload)


	def _output_json(self, payload):

		from django.core.serializers.json import simplejson

		if "callback" in self.request.DATA:
			return self.request.DATA["callback"] + "(%s);" % simplejson.dumps(payload)

		if hasattr(self, "sexy"):
			return simplejson.dumps(payload, indent=4)

		return simplejson.dumps(payload)


	def _validate_request(self, required):

		from django.core.exceptions import ValidationError

		check = self.request.DATA
		for k in required.keys():

			if k not in check:
				raise ValidationError("This method requires the following arguments: %s" % ", ".join(required))

			if required[k] == int:
				try:
					for element in check[k]:
						int(element)
				except ValueError:
					raise ValidationError("\"%s\" must be numeric" % k)

			elif required[k] == float:
				try:
					for element in check[k]:
						float(element)
				except ValueError:
					raise ValidationError("\"%s\" must be a floating point number")


	def _check_authenticated(self):
		"""
			This is Bad Form.  You don't setup the session in the same method
			in which you check its validity.
		"""

		from base64 import b64decode
		from django.core.exceptions import PermissionDenied
		from django.contrib.auth import authenticate, login

		try:
			uname, passwd = b64decode(self.request.META["HTTP_AUTHORIZATION"].split()[1]).split(':')
			user = authenticate(username=uname, password=passwd)
			if user is not None:
				if user.is_active:
					login(self.request, user)
					self.request.user = user
		except KeyError:
			pass

		if not self.request.user.is_authenticated():
			raise PermissionDenied("You must be logged in to do that.")


	def _authenticate_signature(self):
		"""
			Basic OAuth authentication.  Thankfully, we don't have to
			implement the full 3-legged authentication process as this is a
			closed system.
		"""

		from django.conf import settings

		if not hasattr(settings, "REST_USE_OAUTH") or not settings.REST_USE_OAUTH:
			return self.request.REQUEST

		import re, oauth2

		from django.core.exceptions import ValidationError
		from django.db.utils import IntegrityError

		from django_rest.models import Consumer, Nonce

		consumer = Consumer.objects.get(pk=1)

		server = oauth2.Server(signature_methods={'HMAC-SHA1': oauth2.SignatureMethod_HMAC_SHA1()})
		token  = oauth2.Token(key=consumer.access_key, secret=consumer.access_sec)

		req = None
		if self.request.method == "POST":
			req = oauth2.Request(method=self.request.method, url=self.request.build_absolute_uri(), parameters=self.request.POST)
		elif self.request.method == "GET":
			req = oauth2.Request(method=self.request.method, url=re.sub(r"\?.*", "", self.request.build_absolute_uri()), parameters=self.request.GET)

		# Nonce Checking
		n = self.request.REQUEST.get("oauth_nonce")
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
			raise ValidationError("OAuth failure: \n%s" % e)
