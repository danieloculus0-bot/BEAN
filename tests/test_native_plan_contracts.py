import pytest
from bean.runtime.plan_contracts import preflight, validate_args, read_path


def test_valid_dependent_sign_plan():
    inputs={"history":[-2,4,6,8]}
    preflight("last_sign",{"history":{"$input":["history"]}},inputs,[])
    preflight("mean_sign",{"history":{"$input":["history"]}},inputs,["last_sign"])
    preflight("compare_numeric",{"left":{"$step":0,"path":["prediction"]},
        "right":{"$step":1,"path":["prediction"]},"abs_tol":0,"rel_tol":0},
        inputs,["last_sign","mean_sign"])


@pytest.mark.parametrize("args",[
    {},{"data":[1,2]}, {"history":{"$input":["missing"]}},
    {"history":{"$input":["history",0]}},{"history":[]},
    {"history":[True,2]},{"history":[float("inf")]},
])
def test_reject_malformed_first_step_before_execution(args):
    with pytest.raises(ValueError):
        preflight("last_sign",args,{"history":[1,2]},[])


def test_reject_wrong_output_field():
    with pytest.raises(ValueError,match="no such output"):
        preflight("compare_numeric",{"left":{"$step":0,"path":["sign"]},
            "right":1,"abs_tol":0,"rel_tol":0},{},["last_sign"])


def test_unknown_tool_still_checks_input_path():
    with pytest.raises(ValueError):
        preflight("custom",{"v":{"$input":["missing"]}}, {}, [])


def test_dynamic_output_contract_checked_at_execution():
    with pytest.raises(ValueError):
        validate_args("compare_numeric",{"left":"1","right":1,"abs_tol":0,"rel_tol":0})


@pytest.mark.parametrize("path",[[True],[-1],["0"],[3]])
def test_reference_does_not_coerce_indices(path):
    with pytest.raises(ValueError):
        read_path([1,2],path)


def test_portable_csv_contract():
    preflight("group_csv_sum",{"text":{"$input":["csv"]},"group":"g","value":"n"},
              {"csv":"g,n\na,1"},[])
    with pytest.raises(ValueError):
        preflight("group_csv_sum",{"text":"g,n","group":"g"}, {}, [])


def test_repair_observed_whole_predictor_output_references():
    from bean.runtime.plan_contracts import repair_unambiguous_refs
    args={"left":{"$step":0,"path":[]},"right":"$step:1.output","abs_tol":0,"rel_tol":0}
    fixed=repair_unambiguous_refs("compare_numeric",args,{},["last_sign","mean_sign"])
    assert fixed["left"]=={"$step":0,"path":["prediction"]}
    assert fixed["right"]=={"$step":1,"path":["prediction"]}
    assert args["left"]["path"]==[]
    preflight("compare_numeric",fixed,{},["last_sign","mean_sign"])


def test_repair_only_single_matching_history_key():
    from bean.runtime.plan_contracts import repair_unambiguous_refs
    args={"history":"$input[0]"}
    assert repair_unambiguous_refs("mean_sign",args,{"history":[1,2]},[])=={
        "history":{"$input":["history"]}}
    assert repair_unambiguous_refs("mean_sign",args,{"history":[1,2],"other":[3]},[])==args
    assert repair_unambiguous_refs("mean_sign",args,{"other":[1,2]},[])==args
    invalid={"history":["$input[0][-1]"]}
    assert repair_unambiguous_refs("last_sign",invalid,{"history":[1,2]},[])==invalid
    with pytest.raises(ValueError):
        preflight("last_sign",invalid,{"history":[1,2]},[])


def test_repair_never_guesses_other_tool_output_or_literal_text():
    from bean.runtime.plan_contracts import repair_unambiguous_refs
    args={"left":{"$step":0,"path":[]},"right":1,"abs_tol":0,"rel_tol":0}
    assert repair_unambiguous_refs("compare_numeric",args,{},["numeric_context"])==args
    text={"text":"$input[0]"}
    assert repair_unambiguous_refs("profile_csv",text,{"text":"example"},[])==text
