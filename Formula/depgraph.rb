class Depgraph < Formula
  desc "Explainable dependency graphs for Rust, Go, TypeScript, and JavaScript"
  homepage "https://github.com/TamaT-LLC/depgraph-cli"
  license any_of: ["MIT", "Apache-2.0"]

  depends_on "node@24"

  if OS.mac?
    url "https://github.com/TamaT-LLC/depgraph-cli/releases/download/v0.7.1/depgraph-0.7.1-aarch64-apple-darwin.tar.gz"
    sha256 "2c9d7e94da44807418170ad9a00a55e736c721a4f20e3096410ed6428116ed61"
  elsif Hardware::CPU.arm?
    url "https://github.com/TamaT-LLC/depgraph-cli/releases/download/v0.7.1/depgraph-0.7.1-aarch64-unknown-linux-gnu.tar.gz"
    sha256 "15d9c89e0a3ce33cce2c181a27d7045dfbcc4b768f7732e2b811770de8fb84f1"
  else
    url "https://github.com/TamaT-LLC/depgraph-cli/releases/download/v0.7.1/depgraph-0.7.1-x86_64-unknown-linux-gnu.tar.gz"
    sha256 "7b62a8a924041afac39868ce1e60b863302ae8cfbdc222ee8fdbb87d477c79be"
  end

  on_macos do
    depends_on arch: :arm64
  end

  # Homebrew must not rewrite Node shebangs in checksum-verified release artifacts.
  skip_clean "libexec"

  def install
    # Supply prefix metadata so Homebrew does not move the verified package licenses.
    cp ["LICENSE-APACHE", "LICENSE-MIT"], prefix
    # Packaged workers verify the entire release tree. Preserve every byte and path.
    libexec.install Dir["*"]
    %w[depgraph depgraph-mcp].each do |name|
      (bin/name).write_env_script libexec/"bin"/name, PATH: "#{formula_opt_bin("node@24")}:$PATH"
    end
  end

  def caveats
    <<~EOS
      Go and Rust analysis use your project's existing toolchains and offline dependencies.
      MCP/compiler-precise analysis also requires the matching verified compiler pack;
      see https://github.com/TamaT-LLC/depgraph-cli#readme for setup.
    EOS
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/depgraph --version")
    (testpath/"package.json").write('{"name":"brew-fixture","version":"1.0.0","type":"module"}')
    (testpath/"tsconfig.json").write('{"compilerOptions":{"strict":true},"include":["*.ts"]}')
    (testpath/"index.ts").write("export const value: number = 42;\n")
    store = testpath/"graph.sqlite"
    scan = JSON.parse(shell_output("#{bin}/depgraph --store #{store} scan #{testpath} --json"))
    assert_equal "completed", scan.fetch("status")
    assert_operator scan.dig("coverage", "files_analyzed"), :>, 0
    result = JSON.parse(shell_output("#{bin}/depgraph --store #{store} doctor --json"))
    assert_equal "verified", result.dig("release", "core_integrity")
    assert_equal "completed", result.dig("latest_attempt", "status")
    assert_equal %w[go rust web], result.fetch("workers").map { |worker| worker.fetch("adapter") }.sort
    result.fetch("workers").each { |worker| assert_equal "verified", worker.fetch("integrity") }
  end
end
