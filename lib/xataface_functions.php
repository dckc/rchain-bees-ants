<?php
	#function that checks to see if the user has been authenticated with discord and is a coop member
	function checkIfVerifiedCoop()
	{
		global $ini_array;
		
		$auth =& Dataface_AuthenticationTool::getInstance();
		
		#will return false if the user is not logged in
		if(!$user =& $auth->getLoggedInUser())
		{
			return False;
		}

		$is_verified_coop = $user->val($ini_array['verified_coop_column']);
		
		if($is_verified_coop == 1)
		{
			return True;
		}
		else
		{
			return False;
		}
	}
    
    function crypto_rand_secure($min, $max)
    {
        $range = $max - $min;
        if ($range < 1) return $min; // not so random...
        $log = ceil(log($range, 2));
        $bytes = (int) ($log / 8) + 1; // length in bytes
        $bits = (int) $log + 1; // length in bits
        $filter = (int) (1 << $bits) - 1; // set all lower bits to 1
        do {
            $rnd = hexdec(bin2hex(openssl_random_pseudo_bytes($bytes)));
            $rnd = $rnd & $filter; // discard irrelevant bits
        } while ($rnd > $range);
        return $min + $rnd;
    }

    function getToken($length)
    {
        $token = "";
        $codeAlphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
        $codeAlphabet.= "abcdefghijklmnopqrstuvwxyz";
        $codeAlphabet.= "0123456789";
        $max = strlen($codeAlphabet); // edited

        for ($i=0; $i < $length; $i++) {
            $token .= $codeAlphabet[crypto_rand_secure(0, $max-1)];
        }

        return $token;
    }
    #src: http://us1.php.net/manual/en/function.openssl-random-pseudo-bytes.php#104322
?>