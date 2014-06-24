# django-rest

## Don't Use This

This was written years ago, back when `django-piston` was a thing, and suites like
[tastypie](https://github.com/toastdriven/django-tastypie) and
[django-rest-framework](https://github.com/tomchristie/django-rest-framework/) didn't exist.
Now that these projects are around though, this code is stagnant and lacking in the support
and features you'll find in those projects, so go use them instead.

--

Requires:
    oauth2
    django

Here's an example to get you started:

# views.py

from django_rest.views import RestView
from django_rest.decorators import restrict_methods

class View(RestView):
    """
        Exceptions thrown are handled higher up the stack by returning handy things like Http404
    """

    @restrict_methods("POST","PUT")
	def access(self):
		if self.request.method == "POST":
			return self._access_post()
		elif self.request.method == "PUT":
			return self._access_put()


	def _access_post(self):

		name = self.request.DATA.get("name")
		prod = Product.object.create(name=name)
		return self.CREATED(prod.pk)


	def _access_put(self):

		id   = self.request.DATA["id"]
		name = self.request.DATA["name"]

		prod = Product.object.get(pk=id)
		prod.name = name
		prod.save()

		return self.UPDATED()


# urls.py
from django.conf.urls.defaults import *
from product.views import View as ProductView

# API
urlpatterns = patterns("",
    url(r"^$", ProductView(), {"__method": "access"}, name="product-api"),
)
