cask "openpath" do
  version "0.1.0"
  sha256 "d3b06dbc277abbf6931b2a1c6b0d0bd1282c7e3409542f7f8052f9f741cac868"

  url "https://github.com/TamaT-LLC/openpath/releases/download/v#{version}/openpath-#{version}.zip"
  name "openpath"
  desc "Fuzzy search palette for file open dialogs"
  homepage "https://github.com/TamaT-LLC/openpath"

  livecheck do
    url :url
    strategy :github_latest
  end

  depends_on macos: ">= :sonoma"

  app "openpath.app"

  uninstall quit: "jp.tamat.openpath"

  zap trash: [
    "~/.config/openpath",
    "~/Library/Application Support/openpath",
    "~/Library/Logs/openpath",
    "~/Library/Preferences/jp.tamat.openpath.plist",
  ]
end
