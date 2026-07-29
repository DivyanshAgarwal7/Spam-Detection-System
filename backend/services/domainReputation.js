const dns = require('dns').promises;

class DomainReputationService {
  constructor() {
    this.dnsblServers = [
      'zen.spamhaus.org',
      'bl.spamcop.net',
      'dnsbl.sorbs.net'
    ];
  }

  // IP-based DNSBLs are queried with the IPv4 octets reversed, e.g. 1.2.3.4
  // becomes 4.3.2.1 before the zone suffix is appended.
  reverseIPv4(ip) {
    return ip.split('.').reverse().join('.');
  }

  // Resolve the IPv4 addresses that actually send mail for this domain:
  // look up MX hosts first, then resolve each MX host to its A record(s).
  // If the domain has no MX records, fall back to an A lookup on the bare
  // domain, which is a reasonable approximation used by many spam filters.
  async getMailServerIPs(domain) {
    const ips = new Set();

    let mxRecords;
    try {
      mxRecords = await dns.resolveMx(domain);
    } catch {
      mxRecords = [];
    }

    if (mxRecords && mxRecords.length > 0) {
      for (const mx of mxRecords) {
        try {
          const addresses = await dns.resolve4(mx.exchange);
          addresses.forEach((ip) => ips.add(ip));
        } catch {
          // Ignore failures resolving an individual MX host and continue.
        }
      }
    }

    if (ips.size === 0) {
      try {
        const addresses = await dns.resolve4(domain);
        addresses.forEach((ip) => ips.add(ip));
      } catch {
        // No MX-derived IPs and no A record either; return an empty list.
      }
    }

    return Array.from(ips);
  }

  // Query a single IP against a single DNSBL zone using the correct
  // reversed-octet format, e.g. 127.0.0.2 -> 2.0.0.127.zen.spamhaus.org
  async isListed(ip, server) {
    const query = `${this.reverseIPv4(ip)}.${server}`;
    try {
      const result = await dns.resolve(query, 'A');
      return Boolean(result && result.length > 0);
    } catch {
      // NXDOMAIN/ENOTFOUND (and any other lookup error) means "not listed".
      return false;
    }
  }

  async checkReputation(domain) {
    try {
      const ips = await this.getMailServerIPs(domain);

      if (ips.length === 0) {
        return {
          domain,
          score: 0,
          isSuspicious: false,
          listedIn: 'None',
          checkedIPs: []
        };
      }

      let listedCount = 0;
      let totalChecks = 0;
      const listedDetails = [];

      for (const ip of ips) {
        for (const server of this.dnsblServers) {
          totalChecks++;
          const listed = await this.isListed(ip, server);
          if (listed) {
            listedCount++;
            listedDetails.push(`${ip} on ${server}`);
          }
        }
      }

      const score = totalChecks > 0
        ? Math.min((listedCount / totalChecks) * 100, 100)
        : 0;

      return {
        domain,
        score,
        isSuspicious: score > 50,
        listedIn: listedCount > 0 ? `${listedCount} DNSBL${listedCount > 1 ? 's' : ''}` : 'None',
        checkedIPs: ips,
        listedDetails
      };
    } catch (error) {
      return { domain, score: 0, isSuspicious: false, error: error.message };
    }
  }
}

module.exports = new DomainReputationService();
