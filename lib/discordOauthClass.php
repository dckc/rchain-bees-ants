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
			
			#Get a list of members in the rchain guild
			$guild_members = $discord->guild->listGuildMembers(['guild.id' => intval($this->ini_array['rchain_guild_id']), 'limit' => 1000]);
			
			#Search the guild members for the authenticated user. Once found, list all of the roles that member belongs to.
			$user_roles = $discordHelperClass->getRolesOfUser($guild_members, $user->getUsername(), $user->getDiscriminator());
			if($user_roles === False)
			{
				$this->printError("Your discord user is not in the RChain guild");
			}
			
			#now check the member has the required role
			$is_user_coop_member = $discordHelperClass->checkIfUserHasRoleId($user_roles, $this->ini_array['discord_coop_role_id']);

			if($is_user_coop_member === False)
			{
				$this->printError("Your discord user is not in the coop role in the RChain discord guild");
			}


			// $mem_params = ['guild.id' => intval($this->ini_array['rchain_guild_id']),
				       // 'user.id' => intval($user->getId())];
			// try {
			  // $member = $discord->guild->getGuildMember($mem_params);
			// }catch (Exception $e) {
				// $this->printError('cannot getGuildMember');
			// }
			// $coop_member_role = intval($this->ini_array['discord_coop_role']);

			// if(! in_array($coop_member_role, $member->roles))
			// {
				// $this->printError("Your discord user is not in the coop member role in the RChain discord guild.");
			// }

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
