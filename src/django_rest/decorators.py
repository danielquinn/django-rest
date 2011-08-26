from functools import wraps

from django.core.exceptions import PermissionDenied

def restrict_methods(*methods):
	"""

		Decorator that does request method detection/rejection.  Use this on
		every method you have in your API.  Note that in the following example
		we're using a class-based view as that's how the REST API is
		implemented.  I'm reasonably confident that this decorator will *not*
		work in the old-style function-based views.

		Usage:

		    class MyView(RestView):
		        @restrict_methods("POST", "PUT")
		        def my_view(self, request):
		            ....

	"""

	def _inner_restrict_methods(fn):

		def wrapped(instance, request, *a, **kwa):
			if request.method not in methods:
				raise PermissionDenied(methods)

			return fn(instance, request, *a, **kwa)

		return wraps(fn)(wrapped)

	return _inner_restrict_methods
