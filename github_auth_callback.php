<?php
#show errors for debugging.
#ini_set('display_errors', 1);
#ini_set('display_startup_errors', 1);
#error_reporting(E_ALL);

session_start();

require __DIR__ . '/lib/xataface_functions.php';

#get config
$ini_array = parse_ini_file("conf.ini");
$client_id = $ini_array['github_app_client_id'];
$client_secret = $ini_array['github_app_client_secret'];
$url = $ini_array['github_api_url'];

#if there is no code, then they haven't been redirected here from github, so lets send them to github
if(!array_key_exists('code', $_GET) || !isset($_GET['code']))
{
	$auth_url = 'https://github.com/login/oauth/authorize?client_id='.$client_id;
    header('Location: '.$auth_url);
}

$code = $_GET['code'];

$postdata = http_build_query(
    array(
        'client_id' => $client_id,
        'client_secret' => $client_secret,
        'code' => $code
    )
);
$opts = array('http' =>
    array(
        'method'  => 'POST',
        'header'  => 'Content-type: application/x-www-form-urlencoded',
        'content' => $postdata
    )
);
$context = stream_context_create($opts);
if(!$result = file_get_contents($url, false, $context))
{
    echo "failed to connect to github";
    exit();
}


#check for error:
if(strpos($result, 'error') !== false) 
{
    echo "Github responded with an error. Cannot login.";
    exit();
}

#first get all general info
$json_url = 'https://api.github.com/user?'.$result;
$options  = array('http' => array('user_agent'=> $_SERVER['HTTP_USER_AGENT']));
$context  = stream_context_create($options);
if(!$response = file_get_contents($json_url, false, $context))
{
    echo "failed to connect to github";
    exit();
}

if(strpos($response, 'error') !== false) 
{
    echo "Github responded with an error. Cannot login.";
    exit();
}

$response = json_decode($response);

#make sure the response contains what we expect:
if(!property_exists($response, 'login') || $response->login == '')
{
    echo "Github response doesn't contain expected data";
    exit();
}

#now the user is authorized from github, so in order to user the built in xataface session management, 
#we need to tell it to login like a normal user. So lets create a temporary password for this session,
#and store it in the database. Then we will submit the login form to xataface with the correct username
#and password for this session.

#now lets write the info to the database as a user. if it doesnt exist, write it, else just update it
$mysqli = new mysqli($ini_array['host'], $ini_array['user'], $ini_array['password'], $ini_array['name']);
if ($mysqli->connect_errno) 
{
    echo "could not connect to database";
    exit();
}


#randomly generate the temporary session token
#$session_token = md5(uniqid(rand(), true));
#this is CSPRNG. Also saved in database as md5
$session_token = getToken(40);

$sql = <<<SQL
INSERT into {users_table} ({username_column}, {password_column},
                           name, location, email, bio, websiteUrl, avatarUrl, createdAt)
VALUES (?, ?,
        ?, ?, ?, ?, ?, ?, ?)
ON DUPLICATE KEY UPDATE
  {username_column}=VALUES({username_column}),
  {password_column}=VALUES({password_column}),
  name=VALUES(name), location=VALUES(location), email=VALUES(email), bio=VALUES(bio),
  websiteUrl=VALUES(websiteUrl), avatarUrl=VALUES(avatarUrl), createdAt=VALUES(createdAt)
SQL;
$sql = str_replace('{users_table}', $ini_array['users_table'], $sql);
$sql = str_replace('{username_column}', $ini_array['username_column'], $sql);
$sql = str_replace('{password_column}', $ini_array['password_column'], $sql);

if(!$stmt = $mysqli->prepare($sql)) {
    echo "cannot prepare SQL statement";
    exit();
}
$login = $response->login;
$created_at = str_replace('T', ' ', $response->created_at);
$created_at = str_replace('Z', '', $response->created_at);

$stmt->bind_param('sssssssss', $response->login, $session_token,
    $response->name, $response->location, $response->email,
    $response->bio, $response->website_url, $response->avatar_url,
    $created_at);

if (!$result = $stmt->execute())
{
    echo "could not write to database";
    print_r($mysqli->error_list);
    exit();
}

#finally, submit the usual form to xataface
?>

<form id='login_form' action="index.php" method="post" class="xataface-login-form">
    <input type="hidden" name="-action" value="login">
    <input type="hidden" name="-redirect" value="">
    <input type="hidden" name="UserName" value="<?php echo htmlspecialchars($login); ?>">
    <input type="hidden" name="Password" value="<?php echo $session_token; ?>">
	<noscript><input type="submit" value="Click here to finish authenticating"></noscript>
</form>

<script>
    document.getElementById("login_form").submit();
</script>