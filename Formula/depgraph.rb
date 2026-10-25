class Depgraph < Formula
  desc "Explainable dependency graphs for Rust, Go, TypeScript, and JavaScript"
  homepage "https://github.com/TamaT-LLC/depgraph-cli"
  license any_of: ["MIT", "Apache-2.0"]

  depends_on "node@24"

  if OS.mac?
    url "https://github.com/TamaT-LLC/depgraph-cli/releases/download/v0.7.3/depgraph-0.7.3-aarch64-apple-darwin.tar.gz"
    sha256 "12c0b7a17a0f0a35e7e7edc8db1ea4552474e970d08d01f154dce3c30532656e"
  elsif Hardware::CPU.arm?
    url "https://github.com/TamaT-LLC/depgraph-cli/releases/download/v0.7.3/depgraph-0.7.3-aarch64-unknown-linux-gnu.tar.gz"
    sha256 "cd31d6ab48a25e75dd45fc953329ea27ded686d6be4d1bd9c29235c4936028d7"
  else
    url "https://github.com/TamaT-LLC/depgraph-cli/releases/download/v0.7.3/depgraph-0.7.3-x86_64-unknown-linux-gnu.tar.gz"
    sha256 "9b654f44d3700a99369c76f89dfec7047db9acce42b6189440b19bbd9b8f89ca"
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
