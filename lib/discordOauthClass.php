<?php
	#testing
	#need to test on guild that I am not a member of.
	#need to give redirect link on error that takes the user back to the page.
	
	use RestCord\DiscordClient;
	
	class discordOauthClass 
	{
		private $ini_array;
		private $provider;
		private $options;
		
		public function __construct()
		{
			global $ini_array;
			$this->ini_array = $ini_array;
			$this->provider = new \Wohali\OAuth2\Client\Provider\Discord([
				'clientId' => $this->ini_array['discord_client_id'],
				'clientSecret' => $this->ini_array['discord_client_secret'],
				'redirectUri' => $this->ini_array['discord_redirect_uri']
			]);
			
			$this->options = [
				'scope' => ['identify'] // array or string
			];
		}
		
		public function getAuthUrl()
		{
			$authUrl = $this->provider->getAuthorizationUrl($this->options);
			return $authUrl;
		}

		public function checkIfUserValidCoopMember()
		{
			#########################
			#First we validate the user
			#########################
			
			if (!isset($_GET['code'])) {		
				$this->printError("Discord code invalid");
				
			} else {

				// Step 2. Get an access token using the provided authorization code
				try 
				{
					$token = $this->provider->getAccessToken('authorization_code', [
						'code' => $_GET['code']
					]);
				}
				catch (Exception $e)
				{
					$this->printError('Invalid authorization code.');
				}

				try {
					#set this to see their guilds instead of user info
					#$this->provider->setResourceUrl("/users/@me/guilds");
					$user = $this->provider->getResourceOwner($token);

				} catch (Exception $e) {
					$this->printError('Failed to get user details from Discord.');
				}
			}

			#########################
			#Second, we check to see if the validated user is in the coop role
			#########################

			$discordHelperClass = new discordHelperClass();
			
			$discord = new DiscordClient(['token' => $this->ini_array['discord_bot_token']]); // Token is required
			$mem_params = ['guild.id' => intval($this->ini_array['rchain_guild_id']),
				       'user.id' => intval($user->getId())];
			try {
			  $member = $discord->guild->getGuildMember($mem_params);
			}catch (Exception $e) {
				$this->printError('cannot getGuildMember');
			}
			$coop_member_role = intval($this->ini_array['discord_coop_role_id']);

			if(! in_array($coop_member_role, $member->roles))
			{
				$this->printError("Your discord user is not in the coop member role in the RChain discord guild.");
			}

			#the user is confirmed to be a coop member now. Lets add it to the database
			return $user;
		}
		
		public function printError($error)
		{
			echo $error;
			exit();
		}
		
	}

?>
