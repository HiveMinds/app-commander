"""Starts a script to control an app."""


from typing import Callable, Dict, List

from typeguard import typechecked
from uiautomator import AutomatorDevice

from src.apkcontroller.helper import export_screen_data_if_valid, launch_app
from src.apkcontroller.org_torproject_android.plot_script_flow import (
    visualise_script_flow,
)
from src.apkcontroller.org_torproject_android.V16_6_3_RC_1.Apk_script import (
    Apk_script,
)
from src.apkcontroller.script_helper import can_proceed, get_start_nodes


@typechecked
def run_script(script: Apk_script, dev: AutomatorDevice) -> None:
    """Runs the incoming script on the phone.

    Script folder structure: src/apkcontroller/app_name/version.py with
    app_name is something like: com_whatsapp_android (not: Whatsapp). It
    is derived from how your android dev calls the app, with the dots
    replaced by underscores. E.g. com.whatsapp.android or something like
    that.
    """
    visualise_script_flow(
        G=script.script_graph,
        app_name=script.script_description["app_name"].replace(".", "_"),
        app_version=script.script_description["version"]
        .replace(".", "_")
        .replace(" ", "_"),
    )

    # Open the app.
    app_name = script.script_description["app_name"]
    launch_app(app_name)

    expected_screens: List[int] = get_start_nodes(script.script_graph)

    _, screen_nr = can_proceed(
        dev=dev,
        expected_screennames=expected_screens,
        retry=True,
        script=script,
    )
    script.script_description["past_screens"] = [screen_nr]

    next_actions = "filler"
    retry: bool = False  # For the first screen, do a quick scope because it is
    # known already.
    while next_actions is not None:
        _, screen_nr = can_proceed(
            dev=dev,
            expected_screennames=expected_screens,
            retry=retry,
            script=script,
        )
        retry = True
        screen = script.script_graph.nodes[screen_nr]["Screen"]
        print(f"screen_nr={screen_nr}")

        # Export the data of the screens if they happen to be found in the
        # dev already.
        export_screen_data_if_valid(
            dev=dev,
            overwrite=script.script_description["overwrite"],
            screens=[screen],
        )

        # Get next action
        next_actions = screen.get_next_actions(
            required_objects=screen.required_objects,
            optional_objects=screen.optional_objects,
            history=script.script_description,
        )

        # Perform next action.
        if next_actions is not None:

            # Compose the information needed for the actions.
            additional_info = script.script_description
            additional_info["screen_nr"] = screen_nr
            additional_info["script_graph"] = script.script_graph

            # Perform the actual action.
            action_output: Dict = perform_action(
                dev=dev,
                next_actions=next_actions,
                additional_info=additional_info,
            )
            expected_screens = action_output["expected_screens"]
            script.script_description["past_screens"].append(screen_nr)

    print(f'Done with script:{script.script_description["app_name"]}')


@typechecked
def perform_action(
    dev: AutomatorDevice,
    next_actions: Callable,
    additional_info: Dict,
) -> Dict:
    """Performs the first action list in the list of action lists."""
    action_output: Dict = next_actions(
        dev=dev,
        additional_info=additional_info,
    )
    if "expected_screens" not in action_output.keys():
        raise KeyError(
            "Error, the action output did not contain the expected screens."
        )
    return action_output
