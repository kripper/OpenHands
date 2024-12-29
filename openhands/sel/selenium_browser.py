import os
from seleniumbase import SB

os.chdir(os.path.dirname(os.path.abspath(__file__)))

if __name__ == '__main__':
    # Initialize Chrome options
    # sb = SB(uc=True).__enter__()
    with SB(uc=True) as sb:
        driver = sb.driver
        # Save session details for reuse
        command_url = driver.command_executor._client_config._remote_server_addr
        session_id = driver.session_id

        session_script = f"""
url = '{command_url}'
session_id = "{session_id}"
    """

        # Print session details
        print(f"Command URL: {command_url}")
        print(f"Session ID: {session_id}")

        # Write session script to a file
        session_file =  'selenium_session_details.py'
        with open(session_file, 'w') as file:
            file.write(session_script)

        print(f"Session details saved to: {session_file}")
        breakpoint()
