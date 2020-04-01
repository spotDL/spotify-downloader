from spotdl.authorize import AuthorizeBase

import pytest

class TestAbstractBaseClass:
    def test_error_abstract_base_class_authorizebase(self):
        with pytest.raises(TypeError):
            AuthorizeBase()

    def test_inherit_abstract_base_class_authorizebase(self):
        class AuthorizeKid(AuthorizeBase):
            def authorize(self):
                pass

        AuthorizeKid()

