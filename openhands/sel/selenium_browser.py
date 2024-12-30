import os
from seleniumbase import Driver


os.chdir(os.path.dirname(os.path.abspath(__file__)))
home_dir = os.path.expanduser('~')
if __name__ == '__main__':
    # Initialize Chrome options
    driver = Driver(uc=True,user_data_dir=f'{home_dir}/kevin_user_data')
        # Save session details for reuse
    command_url = driver.command_executor._client_config._remote_server_addr
    session_id = driver.session_id

    session_script = f"""
url = '{command_url}'
session_id = "{session_id}"
# driver = create_driver(url,session_id)  
"""

    # Print session details
    print(f"Command URL: {command_url}")
    print(f"Session ID: {session_id}")

    # Write session script to a file
    session_file =  'selenium_session_details.py'
    with open(session_file, 'w') as file:
        file.write(session_script)

    print(f"Session details saved to: {session_file}")

# Run this command to remove the stack trace from the selenium exceptions
# sed -i '43d' /openhands/poetry/openhands-ai-5O4_aCHf-py3.12/lib/python3.12/site-packages/selenium/common/exceptions.py
# https://github.com/SeleniumHQ/selenium/pull/14975