from aiogram.fsm.state import State,StatesGroup
class Flow(StatesGroup):
 token=State();repo_name=State();repo_description=State();existing_repo=State();branch=State();commit_message=State();zip_file=State();workers=State();retries=State();confirm=State();uploading=State()
