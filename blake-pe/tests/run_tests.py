import importlib
import unittest
suite=unittest.TestSuite()
for name in ('test_mail_service','test_inbox_service','test_bugfix_regressions','test_accounts'):
    module=importlib.import_module(name)
    for cls in vars(module).values():
        if isinstance(cls,type) and issubclass(cls,unittest.TestCase) and cls.__module__==module.__name__:
            for method in cls.__dict__:
                if method.startswith('test_'):suite.addTest(cls(method))
result=unittest.TextTestRunner(verbosity=1).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
