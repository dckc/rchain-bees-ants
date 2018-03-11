<?php
    class dataface_modules_XDB {
        function showLoginPrompt()
        {
			global $ini_array;
			$auth_url = 'https://github.com/login/oauth/authorize?client_id='.$ini_array['github_app_client_id'];
			header('Location: '.$auth_url);
        }  
    }
?>
