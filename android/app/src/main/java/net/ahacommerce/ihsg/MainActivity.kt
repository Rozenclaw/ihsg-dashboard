package net.ahacommerce.ihsg

import android.annotation.SuppressLint
import android.content.Intent
import android.graphics.Color
import android.net.Uri
import android.os.Bundle
import android.view.View
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.OnBackPressedCallback
import androidx.appcompat.app.AppCompatActivity
import net.ahacommerce.ihsg.databinding.ActivityMainBinding

/**
 * Thin WebView wrapper around the IHSG dashboard hosted on Streamlit Community
 * Cloud. The dashboard itself updates server-side (git push -> auto redeploy), so
 * this app almost never needs rebuilding — only if the URL in strings.xml changes.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var b: ActivityMainBinding
    private val startUrl: String by lazy { getString(R.string.dashboard_url) }
    private val appHost: String by lazy { Uri.parse(startUrl).host ?: "" }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        b = ActivityMainBinding.inflate(layoutInflater)
        setContentView(b.root)

        val web = b.web
        web.setBackgroundColor(Color.parseColor("#07070B"))
        web.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            databaseEnabled = true
            cacheMode = WebSettings.LOAD_DEFAULT
            loadWithOverviewMode = true
            useWideViewPort = true
            mediaPlaybackRequiresUserGesture = false
            // Keep the default mobile user-agent so Streamlit serves its mobile layout.
        }

        web.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(
                view: WebView,
                request: WebResourceRequest,
            ): Boolean {
                val url = request.url
                val scheme = url.scheme ?: ""
                if (scheme == "http" || scheme == "https") {
                    val host = url.host ?: ""
                    // Keep the dashboard (and any *.streamlit.app) inside the app;
                    // send everything else (news links, AI Studio, etc.) to the browser.
                    return if (host == appHost || host.endsWith(".streamlit.app")) {
                        false
                    } else {
                        openExternally(url); true
                    }
                }
                // mailto:, tel:, intent:, etc. -> hand off to the system.
                openExternally(url)
                return true
            }

            override fun onPageFinished(view: WebView?, url: String?) {
                b.swipe.isRefreshing = false
            }
        }

        web.webChromeClient = object : WebChromeClient() {
            override fun onProgressChanged(view: WebView?, newProgress: Int) {
                b.progress.progress = newProgress
                b.progress.visibility = if (newProgress in 1..99) View.VISIBLE else View.GONE
            }
        }

        // Reports (Decision Helper / Daily Trading .md) and other http(s) downloads
        // hand off to the system so the user can save/share them.
        web.setDownloadListener { url, _, _, _, _ ->
            if (url.startsWith("http")) openExternally(Uri.parse(url))
        }

        b.swipe.setOnRefreshListener { web.reload() }
        b.swipe.setColorSchemeColors(
            Color.parseColor("#818CF8"),
            Color.parseColor("#22D3EE"),
            Color.parseColor("#8B5CF6"),
        )

        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                if (web.canGoBack()) web.goBack() else finish()
            }
        })

        if (savedInstanceState != null) {
            web.restoreState(savedInstanceState)
        } else {
            web.loadUrl(startUrl)
        }
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        b.web.saveState(outState)
    }

    private fun openExternally(uri: Uri) {
        try {
            startActivity(Intent(Intent.ACTION_VIEW, uri))
        } catch (_: Exception) {
            // No app to handle this URI — ignore silently.
        }
    }
}
