<?php
// error reporting for debugging
// ini_set('display_errors', 1);
// error_reporting(1);
// ini_set('error_reporting', E_ALL);
$ini_array = parse_ini_file("conf.ini");

// Include the Xataface API
require_once $ini_array['xataface_location'];
  
// Include custom code
require __DIR__ . '/vendor/autoload.php';
require __DIR__ . '/lib/xataface_functions.php';
require __DIR__ . '/lib/discordHelperClass.php';
require __DIR__ . '/lib/discordOauthClass.php';
require __DIR__ . '/lib/discordOauthFunctions.php';

#Check to see if we need to redirect to redirect to discord oauth before headers sent
#had to use this janky workaround because the action.ini file doesnt let me execute arbitrary php to determine the correct url.
if(checkForDiscordRedirect())
{
	$auth_url = getDiscordAuthUrl();
    header('Location: ' . $auth_url);
}


// Initialize Xataface framework
df_init(__FILE__, 'xataface-2.1.3')->display();
    // first parameter is always the same (path to the current script)
    // 2nd parameter is relative URL to xataface directory (used for CSS files and javascripts)
  