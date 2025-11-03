import ast
import datetime
import logging
import time
import types
from collections import OrderedDict

from dateutil import relativedelta
from django.conf import settings
from django.utils.functional import Promise, SimpleLazyObject

from poms.expressions_engine.exceptions import (
    AttributeDoesNotExist,
    ExpressionEvalError,
    ExpressionSyntaxError,
    FunctionNotDefined,
    InvalidExpression,
    NameNotDefined,
    _Break,
    _Return,
)
from poms.expressions_engine.functions import (
    FINMARS_FUNCTIONS,
    SimpleEval2Def,
    _parse_bool,
    _parse_date,
    _parse_number,
    _print,
)

_l = logging.getLogger("poms.formula")

MAX_STR_LEN = 20000
# MAX_EXPONENT = 4000000  # highest exponent
MAX_EXPONENT = 10000  # highest exponent
# MAX_SHIFT = 1000
MAX_SHIFT = 10
MAX_LEN = 1000


def _op_power(a, b):
    """a limited exponent/to-the-power-of function, for safety reasons"""
    if abs(a) > MAX_EXPONENT or abs(b) > MAX_EXPONENT:
        raise InvalidExpression(f"Invalid exponent, max exponent is {MAX_EXPONENT}")
    return a**b


def _op_mult(a, b):
    # """ limit the number of times a string can be repeated... """
    # if isinstance(a, int) and a * len(b) > MAX_STRING_LENGTH:
    #         raise InvalidExpression("Sorry, a string that long is not allowed")
    #     elif isinstance(b, int) and b * len(a) > MAX_STRING_LENGTH:
    #         raise InvalidExpression("Sorry, a string that long is not allowed")
    if isinstance(a, str):
        raise TypeError(f"Can't convert '{type(a).__name__}' object to str implicitly")
    if isinstance(b, str):
        raise TypeError(f"Can't convert '{type(b).__name__}' object to str implicitly")
    return a * b


def _op_add(a, b):
    """string length limit again"""
    if isinstance(a, str) and isinstance(b, str) and len(a) + len(b) > MAX_STR_LEN:
        raise InvalidExpression("Sorry, adding those two strings would make a too long string.")
    return a + b


def _op_lshift(a, b):
    if b > MAX_SHIFT:
        raise InvalidExpression(f"Invalid left shift, max left shift is {MAX_SHIFT}")
    return a << b


OPERATORS = {
    ast.Is: lambda a, b: a is b,
    ast.IsNot: lambda a, b: a is not b,
    ast.In: lambda a, b: a in b,
    ast.NotIn: lambda a, b: a not in b,
    ast.Add: _op_add,
    ast.BitAnd: lambda a, b: a & b,
    ast.BitOr: lambda a, b: a | b,
    ast.BitXor: lambda a, b: a ^ b,
    ast.Div: lambda a, b: a / b,
    ast.FloorDiv: lambda a, b: a // b,
    ast.LShift: _op_lshift,
    ast.RShift: lambda a, b: a >> b,
    ast.Mult: _op_mult,
    ast.Pow: _op_power,
    ast.Sub: lambda a, b: a - b,
    ast.Mod: lambda a, b: a % b,
    ast.And: lambda a, b: a and b,
    ast.Or: lambda a, b: a or b,
    ast.Eq: lambda a, b: a == b,
    ast.Gt: lambda a, b: a > b,
    ast.GtE: lambda a, b: a >= b,
    ast.Lt: lambda a, b: a < b,
    ast.LtE: lambda a, b: a <= b,
    ast.NotEq: lambda a, b: a != b,
    ast.Invert: lambda a: ~a,
    ast.Not: lambda a: not a,
    ast.UAdd: lambda a: +a,
    ast.USub: lambda a: -a,
}


class _UserDef:
    def __init__(self, parent, node):
        self.parent = parent
        self.node = node

    def __str__(self):
        return f"<def {self.node.name}>"

    def __repr__(self):
        return f"<def {self.node.name}>"

    def __call__(self, evaluator, *args, **kwargs):
        kwargs = kwargs.copy()
        for i, val in enumerate(args):
            name = self.node.args.args[i].arg
            kwargs[name] = val

        offset = len(self.node.args.args) - len(self.node.args.defaults)
        for i, arg in enumerate(self.node.args.args):
            if arg.arg not in kwargs:
                val = self.parent._eval(self.node.args.defaults[i - offset])
                kwargs[arg.arg] = val

        save_table = self.parent._table
        try:
            self.parent._table = save_table.copy()
            self.parent._table.update(kwargs)
            try:
                ret = self.parent._eval(self.node.body)
            except _Return as e:
                ret = e.value
        finally:
            self.parent._table = save_table

        return ret


FUNCTIONS = FINMARS_FUNCTIONS


empty = object()

SAFE_TYPES = (
    bool,
    int,
    float,
    str,
    list,
    tuple,
    dict,
    OrderedDict,
    datetime.date,
    datetime.timedelta,
    datetime.datetime,
    relativedelta.relativedelta,
    SimpleEval2Def,
    _UserDef,
)


class SimpleEval2:
    def __init__(
        self,
        names=None,
        max_time=None,
        add_print=False,
        allow_assign=False,
        now=None,
        context=None,
    ):
        # st = time.perf_counter()

        self.max_time = max_time or 60 * 30  # 30 min
        # self.max_time = 10000000000
        self.start_time = 0
        self.tik_time = 0
        self.allow_assign = allow_assign
        self.context = context if context is not None else {}
        # self.imperial_mode = context.get('imperial_mode', False)

        self.expr = None
        self.expr_ast = None
        self.result = None

        _globals = {f.name: f for f in FUNCTIONS}
        if callable(now):
            _globals["now"] = SimpleEval2Def("now", now)
        elif isinstance(now, datetime.date):
            _globals["now"] = SimpleEval2Def("now", lambda: now)

        # _globals['transaction_import'] = {f.name: f for f in TRANSACTION_IMPORT_FUNCTIONS}

        _globals["globals"] = SimpleEval2Def("globals", lambda: _globals)
        _globals["locals"] = SimpleEval2Def("locals", lambda: self._table)

        _globals["true"] = True
        _globals["false"] = False

        if names:
            _globals.update(names)

        if add_print:
            _globals["print"] = _print

        self._table = _globals

    @staticmethod
    def try_parse(expr):
        if not expr:
            raise InvalidExpression("Empty expression")
        try:
            return ast.parse(expr)
        except SyntaxError as e:
            raise ExpressionSyntaxError(e) from e
        except Exception as e:
            raise InvalidExpression(e) from e

    def check_time(self):
        if settings.DEBUG:
            return
        self.tik_time = time.time()
        if self.tik_time - self.start_time > self.max_time:
            raise InvalidExpression(f"Execution exceeded time limit, max runtime is {self.max_time}")

    @staticmethod
    def is_valid(expr):
        try:
            SimpleEval2.try_parse(expr)
            return True
        except Exception:
            return False

    def has_var(self, name):
        return name in self._table

    def get_var(self, name, default):
        try:
            return self._find_name(name)
        except NameNotDefined:
            return default

    def _find_name(self, name):
        try:
            val = self._table[name]
            return self._check_value(val)
        except (IndexError, KeyError, TypeError) as e:
            raise NameNotDefined(name) from e

    def _check_value(self, val):
        # from django.db import models
        if val is None:
            return None
        elif isinstance(val, SAFE_TYPES):
            return val
        # elif isinstance(val, models.Model):
        else:
            # return get_model_data_ext(val, many=False, context=self.context)
            key = (type(val), getattr(val, "pk", getattr(val, "id", None)))
            if key in self._table:
                val = self._table[key]
            else:
                val = get_model_data_ext(val, context=self.context)
                self._table[key] = val
            return val

    def eval(self, expr, names=None):
        if not expr:
            raise InvalidExpression("Empty expression")

        self.expr = expr
        self.expr_ast = SimpleEval2.try_parse(expr)

        save_table = self._table
        self._table = save_table.copy()
        if names:
            for k, v in names.items():
                self._table[k] = v
        try:
            self.start_time = time.time()
            self.result = self._eval(self.expr_ast.body)
            return self.result
        except _Return as e:
            return e.value
        except InvalidExpression:
            # _l.debug('InvalidExpression', exc_info=True)
            raise
        except Exception as e:
            # _l.debug('Exception', exc_info=True)
            raise ExpressionEvalError(e) from e
        finally:
            self._table = save_table

    def _eval(self, node):
        # _l.debug('%s - %s - %s', node, type(node), node.__class__)
        # self.tik_time = time.time()
        # if self.tik_time - self.start_time > self.max_time:
        #     raise InvalidExpression("Execution exceeded time limit, max runtime is %s" % self.max_time)
        self.check_time()

        if isinstance(node, list | tuple):
            return self._on_many(node)

        op = f"_on_ast_{type(node).__name__}"
        if hasattr(self, op):
            return getattr(self, op)(node)

        raise InvalidExpression(f"Sorry, {type(node).__name__} is not available in this evaluator")

    def _on_many(self, node):
        ret = None
        for n in node:
            ret = self._eval(n)
        return ret

    def _on_ast_Assign(self, node):
        if not self.allow_assign:
            raise InvalidExpression(f"Sorry, {type(node).__name__} is not available in this evaluator")

        ret = self._eval(node.value)
        for t in node.targets:
            if isinstance(t, ast.Name):
                self._table[t.id] = ret
            elif isinstance(t, ast.Subscript):
                obj = self._eval(t.value)
                obj[self._eval(t.slice)] = ret
            elif isinstance(t, ast.Attribute):
                # TODO: check security
                obj = self._eval(t.value)
                if isinstance(obj, dict | OrderedDict):
                    obj[t.attr] = ret
                else:
                    raise ExpressionSyntaxError("Invalid assign")
                    # raise ExpressionSyntaxError('Invalid assign')
            else:
                raise ExpressionSyntaxError("Invalid assign")
        return ret

    def _on_ast_If(self, node):
        return self._eval(node.body) if self._eval(node.test) else self._eval(node.orelse)

    def _on_ast_For(self, node):
        ret = None
        for val in self._eval(node.iter):
            self._table[node.target.id] = val
            try:
                ret = self._eval(node.body)
            except _Break:
                break
        return ret

    def _on_ast_While(self, node):
        ret = None
        while self._eval(node.test):
            try:
                ret = self._eval(node.body)
            except _Break:
                break
        return ret

    def _on_ast_Break(self, node):
        raise _Break()

    def _on_ast_FunctionDef(self, node):
        # self.local_functions[node.name] = node
        self._table[node.name] = _UserDef(self, node)

    def _on_ast_Pass(self, node):
        return None

    def _on_ast_Try(self, node):
        ret = None
        try:
            ret = self._eval(node.body)
        except Exception:
            if node.handlers:
                for n in node.handlers:
                    # ast.ExceptHandler
                    if n.body:
                        ret = self._eval(n.body)
        else:
            if node.orelse:
                ret = self._eval(node.orelse)
        finally:
            if node.finalbody:
                ret = self._eval(node.finalbody)

        return ret

    def _on_ast_Num(self, node):
        return node.n

    def _on_ast_Str(self, node):
        if len(node.s) > MAX_STR_LEN:
            raise ExpressionEvalError(
                f"String Literal in statement is too long! ({len(node.s)}, when {MAX_STR_LEN} is max)"
            )
        return node.s

    def _on_ast_NameConstant(self, node):
        return node.value

    def _on_ast_Constant(self, node):
        return node.value

    def _on_ast_Dict(self, node):
        d = {}
        for k, v in zip(node.keys, node.values, strict=False):
            k = self._eval(k)  # noqa: PLW2901
            v = self._eval(v)  # noqa: PLW2901
            d[k] = v
            if len(d) > MAX_LEN:
                raise ExpressionEvalError("Max dict length.")
        return d

    def _on_ast_List(self, node):
        d = []
        for v in node.elts:
            v = self._eval(v)  # noqa: PLW2901
            d.append(v)
            if len(d) > MAX_LEN:
                raise ExpressionEvalError("Max list/tuple/set length.")
        return d

    def _on_ast_Tuple(self, node):
        return tuple(self._on_ast_List(node))

    def _on_ast_Set(self, node):
        return set(self._on_ast_List(node))

    def _on_ast_UnaryOp(self, node):
        return OPERATORS[type(node.op)](self._eval(node.operand))

    def _on_ast_BinOp(self, node):
        return OPERATORS[type(node.op)](self._eval(node.left), self._eval(node.right))

    def _on_ast_BoolOp(self, node):
        if isinstance(node.op, ast.And):
            # return all((self._eval(v) for v in node.values))
            res = False
            for v in node.values:
                res = self._eval(v)
                if not res:
                    return False
            return res
        elif isinstance(node.op, ast.Or):
            # return any((self._eval(v) for v in node.values))
            res = True
            for v in node.values:
                res = self._eval(v)
                if res:
                    return res
            return res

    def _on_ast_Compare(self, node):
        return OPERATORS[type(node.ops[0])](self._eval(node.left), self._eval(node.comparators[0]))

    def _on_ast_IfExp(self, node):
        return self._eval(node.body) if self._eval(node.test) else self._eval(node.orelse)

    def _on_ast_Call(self, node):
        f = self._eval(node.func)
        if not callable(f):
            raise FunctionNotDefined(node.func.id)

        f_args = [self._eval(a) for a in node.args]
        f_kwargs = {k.arg: self._eval(k.value) for k in node.keywords}

        try:
            if node.func.attr in ["append", "pop", "remove"]:
                return f(*f_args)
        except Exception:
            pass
            # TODO check why error is occuring
            # _l.error("append do not work %s" % e)

        return f(self, *f_args, **f_kwargs)

    def _on_ast_Return(self, node):
        val = self._eval(node.value)
        raise _Return(val)

    def _on_ast_Name(self, node):
        return self._find_name(node.id)

    def _on_ast_Subscript(self, node):
        val = self._eval(node.value)
        index_or_key = self._eval(node.slice)
        try:
            val = val[index_or_key]
            return self._check_value(val)
        except (IndexError, KeyError, TypeError):
            return None

    def _on_ast_Attribute(self, node, val=empty):
        if val is empty:
            val = self._eval(node.value)
        if val is None:
            return None

        if isinstance(val, types.FunctionType):
            val = self._eval(node.value)

        if isinstance(val, dict | OrderedDict):
            try:
                return val[node.attr]
            except (IndexError, KeyError, TypeError) as e:
                # _l.debug('AttributeDoesNotExist.node %s' % node)
                # _l.debug('AttributeDoesNotExist.node.attr %s' % node.attr)
                # _l.debug('AttributeDoesNotExist.node.value %s' % node.value)
                # _l.debug('AttributeDoesNotExist.val %s' % val)

                raise AttributeDoesNotExist(node.attr) from e

        elif isinstance(val, list):
            # _l.debug("list here? %s" % val)
            # _l.debug("list here? node.value %s" % node.value)
            # _l.debug("list here? node.attr %s" % node.attr)
            if node.attr in ["append", "pop", "remove"]:
                return getattr(val, node.attr)
        elif isinstance(val, datetime.date):
            if node.attr in ["year", "month", "day"]:
                return getattr(val, node.attr)

        elif isinstance(val, datetime.timedelta):
            if node.attr in ["days"]:
                return getattr(val, node.attr)

        elif isinstance(val, relativedelta.relativedelta):
            if node.attr in [
                "years",
                "months",
                "days",
                "leapdays",
                "year",
                "month",
                "day",
                "weekday",
            ]:
                return getattr(val, node.attr)

        # _l.info('AttributeDoesNotExist.val %s' % val)
        # _l.info('AttributeDoesNotExist.node %s' % node.__dict__)

        raise AttributeDoesNotExist(node.attr)

    def _on_ast_Index(self, node):
        return self._eval(node.value)

    def _on_ast_Expr(self, node):
        return self._eval(node.value)

    def _on_ast_Slice(self, node):
        lower = upper = step = None
        if node.lower is not None:
            lower = self._eval(node.lower)
        if node.upper is not None:
            upper = self._eval(node.upper)
        if node.step is not None:
            step = self._eval(node.step)
        return slice(lower, upper, step)


def validate(expr):
    from rest_framework.exceptions import ValidationError

    try:
        SimpleEval2.try_parse(expr)
        # try_parse(expr)
    except InvalidExpression as e:
        raise ValidationError(f"Invalid expression: {repr(e)}") from e


def safe_eval(
    s,
    names=None,
    max_time=None,
    add_print=False,
    allow_assign=True,
    now=None,
    context=None,
):
    # st = time.perf_counter()

    e = SimpleEval2(
        names=names,
        max_time=max_time,
        add_print=add_print,
        allow_assign=allow_assign,
        now=now,
        context=context,
    )
    result = e.eval(s)

    # _l.debug('safe_eval done %s : %s' % (s, "{:3.3f}".format(time.perf_counter() - st)))

    return result


def safe_eval_with_logs(
    s,
    names=None,
    max_time=None,
    add_print=False,
    allow_assign=True,
    now=None,
    context=None,
):
    e = SimpleEval2(
        names=names,
        max_time=max_time,
        add_print=add_print,
        allow_assign=allow_assign,
        now=now,
        context=context,
    )
    if "log" not in context:
        context["log"] = ""

    return e.eval(s), context["log"]


def validate_date(val):
    return _parse_date(val)


def validate_num(val):
    return _parse_number(val)


def validate_bool(val):
    print(f"validate_bool val {val}")

    return _parse_bool(val)


def register_fun(name, callback):
    if not callable(callback):
        raise InvalidExpression("Bad function callback")
    if name is None:
        raise InvalidExpression("Invalid function name")
    if name is FUNCTIONS:
        raise InvalidExpression("Function with this name already registered")

    if isinstance(callback, SimpleEval2Def):
        FUNCTIONS[name] = callback
    else:
        FUNCTIONS[name] = SimpleEval2Def(name, callback)


def value_prepare(orig):
    def _dict(data):
        ret = OrderedDict()

        # from poms.obj_attrs.models import GenericAttributeType

        for k, v in data.items():
            # if k == 'attributes':
            #
            #     if 'attributes' not in ret:
            #         ret[k] = {}
            #
            #     # oattrs = _value(v)
            #     # nattrs = OrderedDict()
            #     # for attr in oattrs:
            #     #     attr_t = attr['attribute_type']
            #     #     attr_n = attr_t['user_code']
            #     #     val_t = attr_t['value_type']
            #     #     if val_t == GenericAttributeType.CLASSIFIER:
            #     #         attr['value'] = attr['classifier']
            #     #     elif val_t == GenericAttributeType.NUMBER:
            #     #         attr['value'] = attr['value_float']
            #     #     elif val_t == GenericAttributeType.DATE:
            #     #         attr['value'] = attr['value_date']
            #     #     elif val_t == GenericAttributeType.STRING:
            #     #         attr['value'] = attr['value_string']
            #     #     else:
            #     #         attr['value'] = None
            #     #     nattrs[attr_n] = attr
            #     # ret[k] = nattrs
            #
            #     oattrs = _value(v)
            #     nattrs = OrderedDict()
            #     for attr in oattrs:
            #         attr_t = attr['attribute_type']
            #         attr_n = attr_t['user_code']
            #         val_t = attr_t['value_type']
            #
            #         if val_t == GenericAttributeType.CLASSIFIER:
            #
            #             if attr['classifier']:
            #                 ret[k][attr_n] = attr['classifier']['name']
            #             else:
            #                 ret[k][attr_n] = None
            #         elif val_t == GenericAttributeType.NUMBER:
            #             ret[k][attr_n] = attr['value_float']
            #         elif val_t == GenericAttributeType.DATE:
            #             ret[k][attr_n] = str(attr['value_date'])
            #         elif val_t == GenericAttributeType.STRING:
            #             ret[k][attr_n] = attr['value_string']
            #         else:
            #             ret[k][attr_n] = None
            #
            #     # print('ret[k] %s' % ret[k])

            if k.endswith("_object"):
                k = k[:-7]  # noqa: PLW2901
                ret[k] = _value(v)

            elif k not in ret:
                ret[k] = _value(v)
        return ret

    def _list(data):
        ret = []
        for v in data:
            ret.append(_value(v))
        return ret

    def _value(data):
        if data is None:
            return None
        elif isinstance(data, datetime.date | datetime.datetime | Promise):
            return str(data)
        elif isinstance(data, dict | OrderedDict):
            return _dict(data)
        elif isinstance(data, list | tuple | set):
            return _list(data)
        return data

    return _value(orig)


def get_model_data(instance, object_class, serializer_class, many=False, context=None, hide_fields=None):
    def _dumps():
        serializer = serializer_class(instance=instance, many=many, context=context)
        if hide_fields:
            for f in hide_fields:
                serializer.fields.pop(f)
        data = serializer.data
        data = value_prepare(data)
        if isinstance(data, list | tuple):
            for o in data:
                o["object_class"] = object_class
        else:
            data["object_class"] = object_class
        # import json
        # print(json.dumps(data, indent=2))
        return data

    return SimpleLazyObject(_dumps)


def _get_supported_models_serializer_class():
    from poms.accounts.models import Account, AccountType
    from poms.accounts.serializers import (
        AccountEvalSerializer,
        AccountTypeEvalSerializer,
    )
    from poms.clients.models import Client
    from poms.clients.serializers import ClientSerializer
    from poms.counterparties.models import Counterparty, Responsible
    from poms.counterparties.serializers import (
        CounterpartyEvalSerializer,
        ResponsibleEvalSerializer,
    )
    from poms.currencies.models import Currency, CurrencyHistory
    from poms.currencies.serializers import CurrencyEvalSerializer, CurrencyHistorySerializer
    from poms.instruments.models import (
        AccrualCalculationSchedule,
        Country,
        DailyPricingModel,
        GeneratedEvent,
        Instrument,
        InstrumentType,
        PaymentSizeDetail,
        Periodicity,
        PriceHistory,
    )
    from poms.instruments.serializers import (
        AccrualCalculationScheduleSerializer,
        CountrySerializer,
        DailyPricingModelSerializer,
        GeneratedEventSerializer,
        InstrumentEvalSerializer,
        InstrumentTypeEvalSerializer,
        PaymentSizeDetailSerializer,
        PeriodicitySerializer,
        PriceHistorySerializer,
    )
    from poms.integrations.models import PriceDownloadScheme
    from poms.integrations.serializers import PriceDownloadSchemeSerializer
    from poms.portfolios.models import Portfolio
    from poms.portfolios.serializers import PortfolioEvalSerializer
    from poms.strategies.models import Strategy1, Strategy2, Strategy3
    from poms.strategies.serializers import (
        Strategy1EvalSerializer,
        Strategy2EvalSerializer,
        Strategy3EvalSerializer,
    )
    from poms.transactions.models import ComplexTransaction, Transaction
    from poms.transactions.serializers import (
        ComplexTransactionEvalSerializer,
        TransactionEvalSerializer,
    )
    from poms.users.models import Member
    from poms.users.serializers import MemberSerializer
    from poms.vault.models import VaultRecord
    from poms.vault.serializers import VaultRecordSerializer

    return {
        Account: AccountEvalSerializer,
        AccountType: AccountTypeEvalSerializer,
        Counterparty: CounterpartyEvalSerializer,
        Responsible: ResponsibleEvalSerializer,
        Instrument: InstrumentEvalSerializer,
        InstrumentType: InstrumentTypeEvalSerializer,
        Currency: CurrencyEvalSerializer,
        Portfolio: PortfolioEvalSerializer,
        Strategy1: Strategy1EvalSerializer,
        Strategy2: Strategy2EvalSerializer,
        Strategy3: Strategy3EvalSerializer,
        DailyPricingModel: DailyPricingModelSerializer,
        PaymentSizeDetail: PaymentSizeDetailSerializer,
        PriceHistory: PriceHistorySerializer,
        CurrencyHistory: CurrencyHistorySerializer,
        Periodicity: PeriodicitySerializer,
        PriceDownloadScheme: PriceDownloadSchemeSerializer,
        # Transaction: TransactionTextRenderSerializer,
        Transaction: TransactionEvalSerializer,
        ComplexTransaction: ComplexTransactionEvalSerializer,
        GeneratedEvent: GeneratedEventSerializer,
        Member: MemberSerializer,
        Country: CountrySerializer,
        AccrualCalculationSchedule: AccrualCalculationScheduleSerializer,
        Client: ClientSerializer,
        VaultRecord: VaultRecordSerializer,
    }


_supported_models_serializer_class = SimpleLazyObject(_get_supported_models_serializer_class)


def get_model_data_ext(instance, context=None, hide_fields=None):
    from django.db.models import Manager, QuerySet
    from django.db.models.manager import BaseManager

    if instance is None:
        return None

    many = False
    if isinstance(instance, list | tuple):
        if not instance:
            return []
        many = True
        model = instance[0].__class__
    elif isinstance(instance, QuerySet):
        if not instance:
            return []
        many = True
        model = instance.model
    elif isinstance(instance, Manager | BaseManager):
        if not instance:
            return []
        many = True
        model = instance.model
        instance = instance.all()
    elif instance:
        model = instance.__class__
    else:
        return None
    object_class = str(model.__name__)

    try:
        serializer_class = _supported_models_serializer_class[model]
    except KeyError as e:
        raise InvalidExpression(f"'{model}' can't serialize") from e
    return get_model_data(
        instance=instance,
        object_class=object_class,
        serializer_class=serializer_class,
        many=many,
        context=context,
        hide_fields=hide_fields,
    )
